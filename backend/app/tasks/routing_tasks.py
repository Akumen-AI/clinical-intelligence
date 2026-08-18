import logging
import uuid
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.document import Document, DocumentStatus
from app.models.extracted_field import ExtractedField
from app.services.confidence_router import route_extraction_result, RoutingResult

logger = logging.getLogger("app.tasks.routing_tasks")


@celery_app.task(bind=True, max_retries=3, default_retry_delay=2)
def route_document_fields(self, document_id: str, actor_user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Celery task to route document fields based on confidence scores.
    Loads extraction result from DB for document_id, calls route_extraction_result(),
    and logs outcome at INFO level.
    Retries up to 3 times with exponential backoff on transient errors.
    """
    logger.info(f"[Task] Starting field routing for document_id: {document_id}")
    db: Session = SessionLocal()
    try:
        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            raise ValueError(f"Document with ID '{document_id}' not found")

        fields = (
            db.query(ExtractedField)
            .filter(ExtractedField.document_id == document_id)
            .all()
        )

        field_dict: Dict[str, Any] = {}
        for f in fields:
            field_dict[f.field_name] = {
                "value": f.raw_value,
                "confidence": f.confidence_score,
            }

        extraction_result = {
            "document_id": document_id,
            "fields": field_dict,
        }

        actor_user_uuid = uuid.UUID(actor_user_id) if actor_user_id else None
        result: RoutingResult = route_extraction_result(extraction_result, db=db, actor_user_id=actor_user_uuid)

        logger.info(
            f"[Task] Routing completed for document {document_id}: "
            f"{len(result.routed_to_canonical)} fields to canonical, "
            f"{len(result.routed_to_review)} fields to review queue. "
            f"(Threshold used: {result.threshold_used:.2f})"
        )

        return {
            "document_id": result.document_id,
            "routed_to_canonical": result.routed_to_canonical,
            "routed_to_review": result.routed_to_review,
            "threshold_used": result.threshold_used,
        }

    except Exception as exc:
        logger.error(
            f"[Task Failure] Error routing fields for document '{document_id}': {exc}"
        )
        try:
            # Exponential backoff retry (2s, 4s, 8s...)
            countdown = 2 ** (self.request.retries + 1)
            raise self.retry(exc=exc, countdown=countdown)
        except self.MaxRetriesExceededError:
            logger.critical(
                f"[Dead-Letter Queue] Routing task permanently failed for document '{document_id}' "
                f"after {self.max_retries} retries. Directing to dead-letter handler."
            )
            # Dead-letter queue handling: update document status to FAILED or pending_review
            try:
                doc = db.query(Document).filter(Document.document_id == document_id).first()
                if doc:
                    doc.status = DocumentStatus.FAILED.value
                    doc.rejection_reason = f"Routing task failed after max retries: {str(exc)}"
                    db.commit()
            except Exception as dberr:
                logger.error(f"Failed to set document state to FAILED: {dberr}")
            raise exc
    finally:
        db.close()
