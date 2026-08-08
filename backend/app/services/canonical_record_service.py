import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.extracted_field import ExtractedField

logger = logging.getLogger("app.services.canonical_record_service")


def upsert_field(
    document_id: str,
    field_name: str,
    value: Any,
    confidence: float,
    db: Optional[Session] = None,
) -> ExtractedField:
    """
    Upserts a high-confidence or human-verified field into the canonical patient record.
    Ensures that verified data enters the canonical store.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        field_rec = (
            db.query(ExtractedField)
            .filter(
                ExtractedField.document_id == document_id,
                ExtractedField.field_name == field_name,
            )
            .first()
        )

        if field_rec:
            field_rec.verified_value = value
            field_rec.verification_status = "canonical_committed"
            field_rec.confidence_score = confidence
        else:
            field_rec = ExtractedField(
                field_id=str(uuid.uuid4()),
                document_id=document_id,
                field_name=field_name,
                raw_value=value,
                verified_value=value,
                confidence_score=confidence,
                verification_status="canonical_committed",
                created_at=datetime.now(timezone.utc),
            )
            db.add(field_rec)

        db.commit()
        db.refresh(field_rec)

        logger.info(
            f"[CanonicalRecordService] Upserted canonical field '{field_name}' "
            f"for document '{document_id}' with confidence {confidence:.2f}"
        )
        return field_rec
    except Exception as e:
        db.rollback()
        logger.error(
            f"[CanonicalRecordService] Failed to upsert field '{field_name}' "
            f"for document '{document_id}': {e}"
        )
        raise e
    finally:
        if close_db:
            db.close()
