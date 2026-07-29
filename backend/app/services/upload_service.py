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

def process_document(db: Session, document_id: str):
    """
    Extension point hook for Epic 1.2 (Image Preprocessing).
    This function will be called asynchronously or as a background task to process queued documents.
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

    # Epic 1.4: Document Classification
    from app.services.classification.factory import get_document_classifier
    from app.config import settings
    import time

    print(f"[Epic 1.4 Hook Triggered] Document ID '{document_id}' is queued for classification.")
    classifier = get_document_classifier()
    
    # Extract actual text from the document for classification.
    # Use the raw file first — preprocessing converts PDFs to image-only PDFs,
    # stripping embedded text. Fall back to processed file for scanned documents
    # where image enhancement may help OCR.
    from app.services.text_extraction_service import extract_text

    ocr_text = extract_text(doc.raw_uri, doc.filetype)
    if not ocr_text and doc.processed_uri:
        ocr_text = extract_text(doc.processed_uri, doc.filetype)

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
    
    doc.document_type = result.document_type
    doc.classification_confidence = result.confidence
    doc.needs_manual_review = result.confidence < settings.DOCUMENT_CLASSIFICATION_THRESHOLD
    doc.status = DocumentStatus.CLASSIFIED.value
    db.commit()
    db.refresh(doc)
    
    # Logging required: provider, model, processing_time, confidence, document_type
    provider = settings.AI_PROVIDER.lower()
    model_name = settings.OLLAMA_MODEL if provider == "ollama" else "gemini-2.5-flash"
    print(f"[Epic 1.4 Hook Success] provider={provider}, model={model_name}, processing_time={class_elapsed_ms}ms, confidence={result.confidence}, document_type={result.document_type}")


def queue_document(db: Session, file: UploadFile) -> Document:
    ext = validate_file(file)
    doc_id = generate_uuid()
    _, relative_path = save_file(file, doc_id)
    doc = create_document(db, doc_id, file.filename, relative_path, ext)
    
    # Extension hook call for Epic 1.2
    process_document(db, doc_id)
    
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

