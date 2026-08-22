import os
import gc
import uuid
import shutil
from typing import List, Tuple, Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.services.validation_service import ValidationService
from app.utils.validators import FileValidationError

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "tiff"}
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")

def ensure_upload_directory_exists(directory_path: str = UPLOAD_DIR) -> str:
    os.makedirs(directory_path, exist_ok=True)
    return directory_path

def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_file_extension(filename: str) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()

def save_file(file: UploadFile, document_id: str, target_dir: str = UPLOAD_DIR) -> Tuple[str, str]:
    ensure_upload_directory_exists(target_dir)
    
    # Sanitize filename to prevent path traversal
    base_filename = os.path.basename(file.filename)
    safe_filename_part = base_filename.replace("..", "").replace("/", "").replace("\\", "")
    if not safe_filename_part:
        safe_filename_part = "unnamed_file"
        
    safe_filename = f"{document_id}_{safe_filename_part}"
    filepath = os.path.join(target_dir, safe_filename)
    
    try:
        file.file.seek(0)
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save file on server: {str(e)}"
        )
    
    # Always use forward slashes for stored relative paths (cross-platform compatibility)
    relative_path = "uploads/" + safe_filename
    return filepath, relative_path

def create_document(
    db: Session,
    document_id: str,
    filename: str,
    filepath: str,
    filetype: str
) -> Document:
    doc = Document(
        document_id=document_id,
        filename=filename,
        raw_uri=filepath,
        filetype=filetype,
        status=DocumentStatus.QUEUED.value
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

def process_document(db: Session, document_id: str, actor_user_id: Optional[uuid.UUID] = None):
    """
    Extension point hook for document processing pipeline.
    Handles Preprocessing, Classification, and Field Extraction.

    Handwriting routing: after the initial PaddleOCR pass, if a high
    proportion of OCR fragments fall below the confidence threshold,
    the document is re-processed through a multimodal vision model
    (Gemini) that can read handwriting directly from the image.
    """
    try:
        from app.services import audit_service
        if actor_user_id:
            audit_service.write_entry(
                db=db,
                actor_user_id=actor_user_id,
                action_type="document_extracted",
                target_entity=f"document:{document_id}",
                rationale="Started preprocessing and extraction"
            )
            
        print(f"[Epic 1.2 Hook Triggered] Document ID '{document_id}' is queued for preprocessing.")
        from app.services.preprocessing_service import preprocess_document_file

        doc = get_document_by_id(db, document_id)
        if not doc:
            print(f"[Epic 1.2 Hook Error] Document ID '{document_id}' not found in database.")
            return

        doc.status = DocumentStatus.PREPROCESSING.value
        db.commit()

        try:
            processed_uri, elapsed_time_ms = preprocess_document_file(doc.raw_uri, doc.filetype)
            doc.processed_uri = processed_uri
            doc.processing_time_ms = elapsed_time_ms
            doc.status = DocumentStatus.PREPROCESSED.value
            db.commit()
            db.refresh(doc)
            print(f"[Epic 1.2 Hook Success] Preprocessed document {document_id} in {elapsed_time_ms}ms")
        except Exception as e:
            doc.rejection_reason = f"Preprocessing failed: {str(e)}"
            doc.status = DocumentStatus.FAILED.value
            db.commit()
            db.refresh(doc)
            print(f"[Epic 1.2 Hook Error] Preprocessing failed for document {document_id}: {str(e)}")
            return

        # Epic 1.4: Document Classification
        from app.services.classification.factory import get_document_classifier
        from app.config import settings
        import time

        doc.status = DocumentStatus.CLASSIFYING.value
        db.commit()
        print(f"[Epic 1.4 Hook Triggered] Document ID '{document_id}' is queued for classification.")
        classifier = get_document_classifier()
        
        # Extract actual text from the document for classification.
        # Use the confidence-exposing variant so we can route handwriting.
        from app.services.text_extraction_service import extract_text, extract_text_with_confidence

        # Track whether this document was routed through handwriting extraction
        handwriting_result = None
        ocr_scores = []

        # Extract text from the best available source.
        # After preprocessing, PDFs are saved as PNGs, so _infer_filetype_from_path
        # in the text extraction service routes them correctly through OCR.
        # Prefer the preprocessed file (denoised/deskewed) for better OCR accuracy
        # and to avoid the heavy _ocr_pdf_pages path on the raw PDF (which would
        # spawn a PaddleOCR subprocess alongside Ollama, risking OOM on low-RAM machines).
        ocr_source = doc.processed_uri or doc.raw_uri
        ocr_text, ocr_scores = extract_text_with_confidence(ocr_source, doc.filetype)

        # Fallback: if preprocessed file yielded no text, try the raw file
        if not ocr_text and doc.processed_uri:
            ocr_text, ocr_scores = extract_text_with_confidence(doc.raw_uri, doc.filetype)

        # --- Handwriting routing decision ---
        # If PaddleOCR confidence scores suggest handwriting/illegibility,
        # route to the multimodal vision model for better extraction.
        if (
            ocr_scores
            and settings.HANDWRITING_EXTRACTION_ENABLED
            and settings.GEMINI_API_KEY
        ):
            from app.services.handwriting.routing import should_route_to_handwriting

            if should_route_to_handwriting(
                ocr_scores,
                confidence_threshold=settings.HANDWRITING_OCR_CONFIDENCE_THRESHOLD,
                proportion_threshold=settings.HANDWRITING_LOW_CONFIDENCE_PROPORTION,
                consecutive_count_threshold=settings.HANDWRITING_CONSECUTIVE_LOW_CONFIDENCE_COUNT,
            ):
                print(
                    f"[Handwriting Routing] Document {document_id} flagged for handwriting extraction "
                    f"({sum(1 for s in ocr_scores if s < settings.HANDWRITING_OCR_CONFIDENCE_THRESHOLD)}"
                    f"/{len(ocr_scores)} fragments below {settings.HANDWRITING_OCR_CONFIDENCE_THRESHOLD} threshold)"
                )
                try:
                    from app.services.handwriting.factory import get_handwriting_extractor

                    hw_extractor = get_handwriting_extractor()
                    # Use the image file for multimodal extraction
                    image_source = doc.processed_uri or doc.raw_uri
                    image_abs_path = os.path.abspath(
                        os.path.join(
                            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            image_source,
                        )
                    )
                    handwriting_result = hw_extractor.extract_from_image(
                        image_abs_path,
                        document_type=None,  # not yet classified
                    )
                    # Use the handwriting-extracted text for classification
                    if handwriting_result.raw_text:
                        ocr_text = handwriting_result.raw_text
                        print(
                            f"[Handwriting Routing] Gemini extracted {len(ocr_text)} chars, "
                            f"{len(handwriting_result.illegible_fields)} illegible fields"
                        )
                except Exception as e:
                    print(f"[Handwriting Routing] Handwriting extraction failed, using PaddleOCR output: {e}")
                    handwriting_result = None

        if not ocr_text:
            print(f"[Epic 1.4] No text could be extracted from document {document_id}. Skipping classification.")
            doc.document_type = "Unknown"
            doc.classification_confidence = 0.0
            doc.needs_manual_review = True
            doc.status = DocumentStatus.CLASSIFIED.value
            db.commit()
            db.refresh(doc)
            return
        
        start_time = time.time()
        result = classifier.classify(ocr_text)
        class_elapsed_ms = int((time.time() - start_time) * 1000)
        
        allowed_types = {"Prescription", "Lab Report", "Discharge Summary", "Referral", "Admission Form", "Unknown"}
        doc.document_type = result.document_type
        doc.classification_confidence = result.confidence
        
        if result.document_type not in allowed_types:
            doc.needs_manual_review = True
            print(f"[Epic 1.4] Document type '{result.document_type}' is not in allowed set. Forcing manual review.")
        else:
            doc.needs_manual_review = result.confidence < settings.DOCUMENT_CLASSIFICATION_THRESHOLD
        doc.status = DocumentStatus.CLASSIFIED.value
        db.commit()
        db.refresh(doc)
        
        from app.services.classification.gemini_classifier import GeminiClassifier
        if isinstance(classifier, GeminiClassifier):
            provider = "gemini"
            model_name = classifier.model_name
        else:
            provider = "ollama"
            model_name = settings.OLLAMA_MODEL
        print(f"[Epic 1.4 Hook Success] provider={provider}, model={model_name}, processing_time={class_elapsed_ms}ms, confidence={result.confidence}, document_type={result.document_type}")

        # Epic 2.2: Extract key clinical fields
        try:
            doc.status = DocumentStatus.EXTRACTING.value
            db.commit()
            from app.services.field_extraction_service import extract_and_persist_fields
            
            # If multimodal handwriting extractor already extracted structured fields,
            # pass them directly so high-quality multimodal extraction is preserved.
            pre_extracted = handwriting_result.fields if handwriting_result and handwriting_result.fields else None
            hw_confidences = handwriting_result.field_confidences if handwriting_result else None

            extract_and_persist_fields(
                db,
                doc,
                ocr_text=ocr_text,
                pre_extracted_fields=pre_extracted,
                field_confidences=hw_confidences,
                actor_user_id=actor_user_id,
            )
            print(f"[Epic 2.2 Hook Success] Key fields extracted and persisted for {doc.document_id}")

            # --- Post-process: apply illegible flags from handwriting extraction ---
            if handwriting_result and handwriting_result.illegible_fields:
                from app.models.extracted_field import ExtractedField

                illegible_set = set(handwriting_result.illegible_fields)
                updated_count = 0
                fields_to_update = (
                    db.query(ExtractedField)
                    .filter(
                        ExtractedField.document_id == document_id,
                        ExtractedField.field_name.in_(illegible_set),
                    )
                    .all()
                )
                for field_record in fields_to_update:
                    field_record.confidence_score = 0.0
                    field_record.verification_status = "illegible"
                    updated_count += 1

                # Any illegible field → document needs manual review
                if updated_count > 0:
                    doc.needs_manual_review = True
                    db.commit()
                    db.refresh(doc)
                    print(
                        f"[Handwriting Routing] Flagged {updated_count} field(s) as illegible "
                        f"for document {document_id}. needs_manual_review=True"
                    )

        except Exception as e:
            import traceback; traceback.print_exc(); print(f"[Epic 2.2 Extraction Warning] Field extraction encountered an issue: {e}")

        # Reclaim any residual memory from preprocessing
        gc.collect()
    except Exception as exc:
        print(f"[Process Document Warning] Background processing error for document {document_id}: {exc}")


async def process_single_upload(
    db: Session,
    file: UploadFile,
    actor_user_id: uuid.UUID,
    client_ip: Optional[str] = None
) -> Document:
    """
    Validates, logs, saves, and queues a single file upload.
    Raises FileValidationError if file fails validation rules.
    """
    try:
        _, ext = await ValidationService.validate_file(file)
    except FileValidationError as e:
        ValidationService.log_rejection(
            db=db,
            filename=file.filename or "unknown",
            reason=e.message,
            client_ip=client_ip,
            http_status=e.status_code
        )
        raise e

    doc_id = generate_uuid()
    _, relative_path = save_file(file, doc_id)
    doc = create_document(db, doc_id, file.filename, relative_path, ext)
    
    # Log accepted attempt
    ValidationService.log_acceptance(db, file.filename, client_ip)
    
    from app.services import audit_service
    audit_service.write_entry(
        db=db,
        actor_user_id=actor_user_id,
        action_type="document_uploaded",
        target_entity=f"document:{doc.document_id}",
        rationale=f"Uploaded document {file.filename}"
    )
    
    # process_document should be called via BackgroundTasks in the router, not here synchronously.
    
    return doc

def get_all_documents(db: Session, needs_review: Optional[bool] = None, document_type: Optional[str] = None) -> List[Document]:
    query = db.query(Document)
    if needs_review is not None:
        query = query.filter(Document.needs_manual_review == needs_review)
    if document_type:
        query = query.filter(Document.document_type == document_type)
    return query.order_by(Document.uploaded_at.desc()).all()

def get_document_by_id(db: Session, document_id: str) -> Optional[Document]:
    return db.query(Document).filter(Document.document_id == document_id).first()

def delete_document(db: Session, document_id: str) -> bool:
    """Delete a document record and all its associated files from disk."""
    doc = get_document_by_id(db, document_id)
    if not doc:
        return False

    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Remove raw file
    if doc.raw_uri:
        raw_path = doc.raw_uri if os.path.isabs(doc.raw_uri) else os.path.join(backend_dir, doc.raw_uri)
        if os.path.exists(raw_path):
            try:
                os.remove(raw_path)
            except Exception as e:
                print(f"[Delete Document] Failed to remove raw file {raw_path}: {e}")

    # Remove processed file
    if doc.processed_uri:
        processed_path = doc.processed_uri if os.path.isabs(doc.processed_uri) else os.path.join(backend_dir, doc.processed_uri)
        if os.path.exists(processed_path):
            try:
                os.remove(processed_path)
            except Exception as e:
                print(f"[Delete Document] Failed to remove processed file {processed_path}: {e}")

    # Clean up any other files in UPLOAD_DIR associated with this document_id
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            if filename == ".gitkeep":
                continue
            if document_id in filename:
                full_path = os.path.join(UPLOAD_DIR, filename)
                if os.path.isfile(full_path):
                    try:
                        os.remove(full_path)
                    except Exception as e:
                        print(f"[Delete Document] Failed to remove associated file {full_path}: {e}")

    # Manually cascade delete associated database records
    try:
        from app.models.extracted_field import ExtractedField
        from app.models.pending_review import PendingReview
        from app.models.canonical_patient_record import CanonicalPatientRecord
        from app.models.clinical_entities import Medication, Diagnosis, LabResult, Vital, Procedure
        from app.models.visit import Visit
        from app.models.rag_chunk import PatientRAGChunk
        from app.models.upload_log import UploadLog
        from app.models.correction_log import CorrectionLog
        from app.models.layout_region import LayoutRegion

        # Delete clinical entities linked to extracted fields
        field_ids = [fid[0] for fid in db.query(ExtractedField.field_id).filter(ExtractedField.document_id == document_id).all()]
        if field_ids:
            db.query(Medication).filter(Medication.source_field_id.in_(field_ids)).delete(synchronize_session=False)
            db.query(Diagnosis).filter(Diagnosis.source_field_id.in_(field_ids)).delete(synchronize_session=False)
            db.query(LabResult).filter(LabResult.source_field_id.in_(field_ids)).delete(synchronize_session=False)
            db.query(Vital).filter(Vital.source_field_id.in_(field_ids)).delete(synchronize_session=False)
            db.query(Procedure).filter(Procedure.source_field_id.in_(field_ids)).delete(synchronize_session=False)

        # Delete canonical records, pending reviews, layout regions, correction logs
        db.query(CanonicalPatientRecord).filter(CanonicalPatientRecord.document_id == document_id).delete(synchronize_session=False)
        db.query(PendingReview).filter(PendingReview.document_id == document_id).delete(synchronize_session=False)
        db.query(ExtractedField).filter(ExtractedField.document_id == document_id).delete(synchronize_session=False)
        db.query(Visit).filter(Visit.document_id == document_id).delete(synchronize_session=False)
        db.query(PatientRAGChunk).filter(PatientRAGChunk.source_document_id == document_id).delete(synchronize_session=False)
        db.query(CorrectionLog).filter(CorrectionLog.document_id == document_id).delete(synchronize_session=False)
        db.query(LayoutRegion).filter(LayoutRegion.document_id == document_id).delete(synchronize_session=False)
        if doc.filename:
            db.query(UploadLog).filter(UploadLog.filename == doc.filename).delete(synchronize_session=False)
    except Exception as e:
        print(f"[Delete Document] Failed to cascade delete related records: {e}")

    db.delete(doc)
    db.commit()
    return True

def delete_all_documents(db: Session) -> int:
    """Delete all document records and clean up all files in the uploads folder (preserving .gitkeep). Returns count deleted."""
    docs = db.query(Document).all()
    count = len(docs)
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    for doc in docs:
        if doc.raw_uri:
            raw_path = doc.raw_uri if os.path.isabs(doc.raw_uri) else os.path.join(backend_dir, doc.raw_uri)
            if os.path.exists(raw_path):
                try:
                    os.remove(raw_path)
                except Exception as e:
                    print(f"[Delete All Documents] Failed to remove raw file {raw_path}: {e}")
        if doc.processed_uri:
            processed_path = doc.processed_uri if os.path.isabs(doc.processed_uri) else os.path.join(backend_dir, doc.processed_uri)
            if os.path.exists(processed_path):
                try:
                    os.remove(processed_path)
                except Exception as e:
                    print(f"[Delete All Documents] Failed to remove processed file {processed_path}: {e}")

    # Clean up any remaining files in UPLOAD_DIR (preserving .gitkeep)
    if os.path.exists(UPLOAD_DIR):
        for filename in os.listdir(UPLOAD_DIR):
            if filename == ".gitkeep":
                continue
            full_path = os.path.join(UPLOAD_DIR, filename)
            if os.path.isfile(full_path):
                try:
                    os.remove(full_path)
                except Exception as e:
                    print(f"[Delete All Documents] Failed to remove orphaned file {full_path}: {e}")

    # Cascade delete all related database records
    try:
        from app.models.extracted_field import ExtractedField
        from app.models.pending_review import PendingReview
        from app.models.canonical_patient_record import CanonicalPatientRecord
        from app.models.clinical_entities import Medication, Diagnosis, LabResult, Vital, Procedure
        from app.models.visit import Visit
        from app.models.rag_chunk import PatientRAGChunk
        from app.models.upload_log import UploadLog
        from app.models.correction_log import CorrectionLog
        from app.models.layout_region import LayoutRegion

        db.query(Medication).delete()
        db.query(Diagnosis).delete()
        db.query(LabResult).delete()
        db.query(Vital).delete()
        db.query(Procedure).delete()
        db.query(CanonicalPatientRecord).delete()
        db.query(PendingReview).delete()
        db.query(ExtractedField).delete()
        db.query(Visit).delete()
        db.query(PatientRAGChunk).delete()
        db.query(CorrectionLog).delete()
        db.query(LayoutRegion).delete()
        db.query(UploadLog).delete()
    except Exception as e:
        print(f"[Delete All Documents] Failed to cascade delete related records: {e}")

    db.query(Document).delete()
    db.commit()
    return count


