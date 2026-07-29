import os
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
    safe_filename = f"{document_id}_{file.filename}"
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
    
    relative_path = os.path.join("uploads", safe_filename)
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
    Extension point hook for Epic 1.2 (Image Preprocessing).
    This function is called for valid, queued documents.
    """
    print(f"[Epic 1.2 Hook Triggered] Document ID '{document_id}' is queued for preprocessing.")
    from app.services.preprocessing_service import preprocess_document_file

    doc = get_document_by_id(db, document_id)
    if not doc:
        print(f"[Epic 1.2 Hook Error] Document ID '{document_id}' not found in database.")
        return

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
        db.commit()
        db.refresh(doc)
        print(f"[Epic 1.2 Hook Error] Preprocessing failed for document {document_id}: {str(e)}")

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
    
    # Epic 1.2 preprocessing hook
    process_document(doc_id)
    # Extension hook call for Epic 1.2
    process_document(db, doc_id)
    
    return doc

def get_all_documents(db: Session) -> List[Document]:
    return db.query(Document).order_by(Document.uploaded_at.desc()).all()

def get_document_by_id(db: Session, document_id: str) -> Optional[Document]:
    return db.query(Document).filter(Document.document_id == document_id).first()
