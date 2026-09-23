import structlog
logger = structlog.get_logger(__name__)

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
from app.services.storage_provider import LocalStorageProvider

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "tiff"}
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
storage_provider = LocalStorageProvider(UPLOAD_DIR)


def ensure_upload_directory_exists(directory_path: str = UPLOAD_DIR) -> str:
    os.makedirs(directory_path, exist_ok=True)
    return directory_path

def generate_uuid() -> str:
    return str(uuid.uuid4())

def get_file_extension(filename: str) -> str:
    if not filename or "." not in filename:
        return ""
    return filename.rsplit(".", 1)[1].lower()

def get_safe_filename(document_id: str, original_filename: str) -> str:
    ext = get_file_extension(original_filename)
    return f"{document_id}.{ext}" if ext else document_id

def save_file(file: UploadFile, document_id: str, target_dir: str = UPLOAD_DIR) -> Tuple[str, str]:
    safe_filename = get_safe_filename(document_id, file.filename)
    
    try:
        filepath = storage_provider.save(file, safe_filename)
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
        patient_id=None,
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
        filename = os.path.basename(doc.raw_uri)
        try:
            storage_provider.delete(filename)
        except Exception as e:
            logger.info(f"[Delete Document] Failed to remove raw file {filename}: {e}")

    # Remove processed file
    if doc.processed_uri:
        filename = os.path.basename(doc.processed_uri)
        try:
            storage_provider.delete(filename)
        except Exception as e:
            logger.info(f"[Delete Document] Failed to remove processed file {filename}: {e}")

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
                        logger.info(f"[Delete Document] Failed to remove associated file {full_path}: {e}")

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
        logger.info(f"[Delete Document] Failed to cascade delete related records: {e}")

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
            filename = os.path.basename(doc.raw_uri)
            try:
                storage_provider.delete(filename)
            except Exception as e:
                logger.info(f"[Delete All Documents] Failed to remove raw file {filename}: {e}")
        if doc.processed_uri:
            filename = os.path.basename(doc.processed_uri)
            try:
                storage_provider.delete(filename)
            except Exception as e:
                logger.info(f"[Delete All Documents] Failed to remove processed file {filename}: {e}")

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
                    logger.info(f"[Delete All Documents] Failed to remove orphaned file {full_path}: {e}")

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
        logger.info(f"[Delete All Documents] Failed to cascade delete related records: {e}")

    db.query(Document).delete()
    db.commit()
    return count


