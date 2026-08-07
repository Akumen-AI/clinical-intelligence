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

def process_document(db: Session, document_id: str):
    """
    Extension point hook for document processing pipeline.
    Handles Preprocessing, Classification, and Field Extraction.
    """
    try:
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
        from app.services.text_extraction_service import extract_text

        # For PDFs, check raw_uri first for embedded digital text (fast and uses zero RAM)
        if doc.filetype.lower() == "pdf":
            ocr_text = extract_text(doc.raw_uri, doc.filetype)
            if not ocr_text and doc.processed_uri:
                ocr_text = extract_text(doc.processed_uri, doc.filetype)
        else:
            ocr_source = doc.processed_uri or doc.raw_uri
            ocr_text = extract_text(ocr_source, doc.filetype)

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
            extract_and_persist_fields(db, doc, ocr_text=ocr_text)
            print(f"[Epic 2.2 Hook Success] Key fields extracted and persisted for {doc.document_id}")
        except Exception as e:
            print(f"[Epic 2.2 Extraction Warning] Field extraction encountered an issue: {e}")

        # Reclaim any residual memory from preprocessing
        gc.collect()
    except Exception as exc:
        print(f"[Process Document Warning] Background processing error for document {document_id}: {exc}")


async def process_single_upload(
    db: Session,
    file: UploadFile,
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
    
    # process_document should be called via BackgroundTasks in the router, not here synchronously.
    
    return doc

def get_all_documents(db: Session) -> List[Document]:
    return db.query(Document).order_by(Document.uploaded_at.desc()).all()

def get_document_by_id(db: Session, document_id: str) -> Optional[Document]:
    return db.query(Document).filter(Document.document_id == document_id).first()

def delete_document(db: Session, document_id: str) -> bool:
    """Delete a document record and its associated files from disk."""
    doc = get_document_by_id(db, document_id)
    if not doc:
        return False

    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    # Remove raw file
    if doc.raw_uri:
        raw_path = os.path.join(backend_dir, doc.raw_uri)
        if os.path.exists(raw_path):
            os.remove(raw_path)

    # Remove processed file
    if doc.processed_uri:
        processed_path = os.path.join(backend_dir, doc.processed_uri)
        if os.path.exists(processed_path):
            os.remove(processed_path)

    db.delete(doc)
    db.commit()
    return True

def delete_all_documents(db: Session) -> int:
    """Delete all document records and their associated files. Returns count deleted."""
    docs = db.query(Document).all()
    count = len(docs)
    backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    for doc in docs:
        if doc.raw_uri:
            raw_path = os.path.join(backend_dir, doc.raw_uri)
            if os.path.exists(raw_path):
                os.remove(raw_path)
        if doc.processed_uri:
            processed_path = os.path.join(backend_dir, doc.processed_uri)
            if os.path.exists(processed_path):
                os.remove(processed_path)

    db.query(Document).delete()
    db.commit()
    return count

