import logging
from app.database import SessionLocal
from app.models.document import Document
from app.services.rag_service import index_document

from app.celery_app import celery_app

logger = logging.getLogger("app.tasks.rag_tasks")

@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def index_document_task(self, document_id: str, correlation_id: str | None = None, actor_id: str | None = None):
    """
    Background task to index a document for RAG after it is linked to a patient.
    Uses verified extracted fields and canonical patient records.
    """
    from app.core.context import set_correlation_id, set_actor_id
    import uuid
    if correlation_id:
        set_correlation_id(correlation_id)
    if actor_id:
        set_actor_id(uuid.UUID(actor_id))
    db = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            logger.error(f"[RAG Task] Document {document_id} not found")
            return
            
        if not doc.patient_id:
            logger.warning(f"[RAG Task] Document {document_id} is not linked to a patient")
            return
            
        # The indexing logic in rag_service.py is now responsible for fetching
        # the strictly verified structured facts. We pass an empty string for the
        # raw OCR text since we strictly do not want to index unverified full text.
        index_document(db, doc, "")
            
    except Exception as e:
        logger.error(f"[RAG Task] Error indexing document {document_id}: {e}")
    finally:
        db.close()
