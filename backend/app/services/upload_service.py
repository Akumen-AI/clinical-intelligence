import os
import uuid
import shutil
from typing import List, Tuple, Optional
from fastapi import UploadFile, HTTPException, status
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus

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

def validate_file(file: UploadFile) -> str:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty"
        )
    
    ext = get_file_extension(file.filename)
    if ext not in ALLOWED_EXTENSIONS:
        allowed_str = ", ".join(sorted(ALLOWED_EXTENSIONS)).upper()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '.{ext}'. Allowed file types are: {allowed_str}"
        )
    return ext

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
        status=DocumentStatus.NEW.value
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

def process_document(document_id: str):
    """
    Extension point hook for Epic 1.2 (Image Preprocessing).
    This function will be called asynchronously or as a background task to process queued documents.
    """
    print(f"[Epic 1.2 Hook Triggered] Document ID '{document_id}' is queued for preprocessing.")

def queue_document(db: Session, file: UploadFile) -> Document:
    ext = validate_file(file)
    doc_id = generate_uuid()
    _, relative_path = save_file(file, doc_id)
    doc = create_document(db, doc_id, file.filename, relative_path, ext)
    
    # Extension hook call for Epic 1.2
    process_document(doc_id)
    
    return doc

def get_all_documents(db: Session) -> List[Document]:
    return db.query(Document).order_by(Document.uploaded_at.desc()).all()

def get_document_by_id(db: Session, document_id: str) -> Optional[Document]:
    return db.query(Document).filter(Document.document_id == document_id).first()
