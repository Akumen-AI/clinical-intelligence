import logging
import time
import os
import gc
import uuid
import shutil
import mimetypes
from typing import Optional
from sqlalchemy.orm import Session
from celery.exceptions import Ignore
from redis import Redis
from redis.exceptions import LockError

from app.celery_app import celery_app
from app.database import Base
import app.database
from app.models.document import Document, DocumentStatus
from app.utils.validators import FileValidationError

logger = logging.getLogger("app.tasks.document_tasks")

# Initialize a standard Redis client for locking (matching celery broker)
redis_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
redis_client = Redis.from_url(redis_url)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=5)
def process_document_task(self, document_id: str, actor_id: Optional[str] = None, correlation_id: Optional[str] = None):
    """
    Celery task to process a document (Epic 1.2, 1.4, 2.2).
    Runs preprocessing, classification, and field extraction sequentially.
    """
    logger.info(f"[Document Task] Starting processing for document {document_id}")
    
    # We set correlation_id into contextvars if provided so audit logs can pick it up
    from app.core.context import set_correlation_id, set_actor_id
    if correlation_id:
        set_correlation_id(correlation_id)
    actor_uuid = uuid.UUID(actor_id) if actor_id else None
    if actor_uuid:
        set_actor_id(actor_uuid)

    db: Session = app.database.SessionLocal()
    try:
        from app.services import audit_service
        from app.services.preprocessing_service import preprocess_document_file

        doc = db.query(Document).filter(Document.document_id == document_id).first()
        if not doc:
            logger.error(f"[Document Task] Document ID '{document_id}' not found in database.")
            return

        # Epic 1.2: Preprocessing
        doc.status = DocumentStatus.PREPROCESSING.value
        db.commit()

        try:
            processed_uri, elapsed_time_ms = preprocess_document_file(doc.raw_uri, doc.filetype)
            doc.processed_uri = processed_uri
            doc.processing_time_ms = elapsed_time_ms
            doc.status = DocumentStatus.PREPROCESSED.value
            db.commit()
            db.refresh(doc)
            logger.info(f"[Document Task] Preprocessed document {document_id} in {elapsed_time_ms}ms")
        except Exception as e:
            doc.rejection_reason = f"Preprocessing failed: {str(e)}"
            doc.status = DocumentStatus.FAILED.value
            db.commit()
            logger.error(f"[Document Task] Preprocessing failed for document {document_id}: {str(e)}")
            raise

        # Epic 1.4: Document Classification
        from app.services.classification.factory import get_document_classifier
        from app.config import settings

        doc.status = DocumentStatus.CLASSIFYING.value
        db.commit()
        classifier = get_document_classifier()
        
        from app.services.text_extraction_service import extract_text_with_confidence

        handwriting_result = None
        ocr_scores = []
        ocr_source = doc.processed_uri or doc.raw_uri
        ocr_text, ocr_scores = extract_text_with_confidence(ocr_source, doc.filetype)

        if not ocr_text and doc.processed_uri:
            ocr_text, ocr_scores = extract_text_with_confidence(doc.raw_uri, doc.filetype)

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
                logger.info(f"[Document Task] Document {document_id} flagged for handwriting extraction")
                try:
                    from app.services.handwriting.factory import get_handwriting_extractor
                    hw_extractor = get_handwriting_extractor()
                    image_source = doc.processed_uri or doc.raw_uri
                    image_abs_path = os.path.abspath(
                        os.path.join(
                            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                            image_source,
                        )
                    )
                    handwriting_result = hw_extractor.extract_from_image(
                        image_abs_path,
                        document_type=None,
                    )
                    if handwriting_result.raw_text:
                        ocr_text = handwriting_result.raw_text
                except Exception as e:
                    logger.warning(f"[Document Task] Handwriting extraction failed, using PaddleOCR output: {e}")
                    handwriting_result = None

        if not ocr_text:
            logger.warning(f"[Document Task] No text could be extracted from document {document_id}. Skipping classification.")
            doc.document_type = "Unknown"
            doc.classification_confidence = 0.0
            doc.needs_manual_review = True
            doc.status = DocumentStatus.CLASSIFIED.value
            db.commit()
            return
        
        start_time = time.time()
        result = classifier.classify(ocr_text)
        class_elapsed_ms = int((time.time() - start_time) * 1000)
        
        allowed_types = {"Prescription", "Lab Report", "Discharge Summary", "Referral", "Admission Form", "Unknown"}
        doc.document_type = result.document_type
        doc.classification_confidence = result.confidence
        
        if result.document_type not in allowed_types:
            doc.needs_manual_review = True
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

        # Epic 2.2: Extract key clinical fields
        doc.status = DocumentStatus.EXTRACTING.value
        db.commit()
        from app.services.field_extraction_service import extract_and_persist_fields
        
        pre_extracted = handwriting_result.fields if handwriting_result and handwriting_result.fields else None
        hw_confidences = handwriting_result.field_confidences if handwriting_result else None

        extract_and_persist_fields(
            db,
            doc,
            ocr_text=ocr_text,
            pre_extracted_fields=pre_extracted,
            field_confidences=hw_confidences,
            actor_user_id=actor_uuid,
        )
        logger.info(f"[Document Task] Key fields extracted and persisted for {doc.document_id}")
        if actor_uuid:
            audit_service.write_entry(
                db=db,
                actor_user_id=actor_uuid,
                action_type="document_extracted",
                target_entity=f"document:{document_id}",
                patient_id=doc.patient_id,
                rationale="Successfully extracted document fields",
                outcome="success",
                context={
                    "provider": provider,
                    "model": model_name
                }
            )

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

            if updated_count > 0:
                doc.needs_manual_review = True
                db.commit()

        # Update final state
        doc.status = DocumentStatus.EXTRACTED.value
        db.commit()
        
    except Exception as exc:
        logger.error(f"[Document Task] Background processing error for document {document_id}: {exc}")
        try:
            # Retry transient failures with exponential backoff (5s, 10s, 20s)
            countdown = self.default_retry_delay * (2 ** self.request.retries)
            raise self.retry(exc=exc, countdown=countdown)
        except self.MaxRetriesExceededError:
            logger.critical(f"[Document Task] Max retries exceeded for document {document_id}. Marking as FAILED.")
            try:
                # Need to use a fresh query in case session is dirty
                db.rollback()
                failed_doc = db.query(Document).filter(Document.document_id == document_id).first()
                if failed_doc:
                    failed_doc.status = DocumentStatus.FAILED.value
                    failed_doc.rejection_reason = f"Background processing failed: {str(exc)}"
                    db.commit()
                if actor_uuid:
                    from app.services import audit_service
                    audit_service.write_entry(
                        db=db,
                        actor_user_id=actor_uuid,
                        action_type="document_extracted",
                        target_entity=f"document:{document_id}",
                        patient_id=None,
                        rationale=f"Failed to extract document fields: {str(exc)}",
                        outcome="failure"
                    )
            except Exception as dberr:
                logger.error(f"[Document Task] Failed to update FAILED status: {dberr}")
            raise exc
    finally:
        gc.collect()
        db.close()


@celery_app.task(bind=True, name="tasks.scan_watched_folder_task")
def scan_watched_folder_task(self):
    """
    Celery Beat task to scan the watched folder for new files.
    Uses a Redis lock to ensure only one worker processes the folder at a time.
    """
    lock_name = "clinical_platform:folder_watcher_lock"
    # Acquire lock for 5 minutes max
    try:
        with redis_client.lock(lock_name, timeout=300, blocking_timeout=1):
            logger.info("[FolderWatcher] Lock acquired, scanning folder.")
            db: Session = app.database.SessionLocal()
            try:
                from app.services.folder_watcher_service import scan_watched_folder_logic
                system_actor = uuid.UUID('00000000-0000-0000-0000-000000000001')
                scan_watched_folder_logic(db, system_actor)
            finally:
                db.close()
    except LockError:
        logger.debug("[FolderWatcher] Lock already acquired by another worker. Skipping scan.")
        raise Ignore()
