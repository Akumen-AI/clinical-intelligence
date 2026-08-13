import logging
from app.database import SessionLocal
from app.models.document import Document
from app.services.rag_service import index_document
from app.services.text_extraction_service import extract_text

logger = logging.getLogger("app.tasks.rag_tasks")

def index_document_task(document_id: str):
    """
    Background task to index a document for RAG after it is linked to a patient.
    """
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            logger.error(f"[RAG Task] Document {document_id} not found")
            return
            
        if not doc.patient_id:
            logger.warning(f"[RAG Task] Document {document_id} is not linked to a patient")
            return
            
        ocr_source = doc.processed_uri or doc.raw_uri
        if not ocr_source:
            logger.warning(f"[RAG Task] Document {document_id} has no URI to extract text from")
            return
            
        # Extract text synchronously since we're in a background task
        # We don't need confidence scores for RAG, just the text
        ocr_text = extract_text(ocr_source, doc.filetype)
        
        if ocr_text:
            index_document(db, doc, ocr_text)
        else:
            logger.warning(f"[RAG Task] No text extracted from document {document_id}")
            
    except Exception as e:
        logger.error(f"[RAG Task] Error indexing document {document_id}: {e}")
    finally:
        db.close()
