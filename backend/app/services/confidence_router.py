import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.pending_review import PendingReview, ReviewStatus, SystemConfig
from app import services as services_pkg
from app.services import canonical_record_service

logger = logging.getLogger("app.services.confidence_router")


@dataclass
class RoutingResult:
    document_id: str
    routed_to_canonical: List[str]
    routed_to_review: List[str]
    threshold_used: float


def get_confidence_threshold_info(db: Optional[Session] = None) -> Tuple[float, str]:
    """
    Returns (threshold_value, source) where source is 'db' or 'env'.
    """
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        config_rec = (
            db.query(SystemConfig)
            .filter(SystemConfig.key == "CONFIDENCE_THRESHOLD")
            .first()
        )
        if config_rec:
            try:
                val = float(config_rec.value)
                return val, "db"
            except ValueError:
                pass
        return settings.CONFIDENCE_THRESHOLD, "env"
    finally:
        if close_db:
            db.close()


def get_confidence_threshold(db: Optional[Session] = None) -> float:
    """
    Returns the active confidence threshold value.
    """
    threshold, _ = get_confidence_threshold_info(db)
    return threshold


def set_confidence_threshold(threshold: float, db: Optional[Session] = None) -> Tuple[float, str]:
    """
    Validates and sets the confidence threshold (must be 0.0 < threshold <= 1.0).
    Persists setting in SystemConfig table.
    """
    if not (0.0 < threshold <= 1.0):
        raise ValueError("Confidence threshold must satisfy 0.0 < threshold <= 1.0")

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        config_rec = (
            db.query(SystemConfig)
            .filter(SystemConfig.key == "CONFIDENCE_THRESHOLD")
            .first()
        )
        if config_rec:
            config_rec.value = str(threshold)
            config_rec.updated_at = datetime.now(timezone.utc)
        else:
            config_rec = SystemConfig(
                key="CONFIDENCE_THRESHOLD",
                value=str(threshold),
                updated_at=datetime.now(timezone.utc),
            )
            db.add(config_rec)

        db.commit()
        logger.info(f"[ConfidenceRouter] Confidence threshold updated to {threshold:.4f}")
        return threshold, "db"
    except Exception as e:
        db.rollback()
        logger.error(f"[ConfidenceRouter] Failed to persist confidence threshold: {e}")
        raise e
    finally:
        if close_db:
            db.close()


def route_extraction_result(
    extraction_result: dict,
    db: Optional[Session] = None,
) -> RoutingResult:
    """
    Iterates over all fields in extraction_result:
      - Fields with confidence >= threshold -> passed to canonical_record_service.upsert_field()
      - Fields with confidence < threshold -> inserted into pending_review table
    Returns RoutingResult.
    """
    document_id = extraction_result.get("document_id", "")
    if not document_id:
        raise ValueError("extraction_result must contain a non-empty 'document_id'")

    fields_data = extraction_result.get("fields", {})

    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        threshold = get_confidence_threshold(db)

        routed_to_canonical: List[str] = []
        routed_to_review: List[str] = []

        pending_records: List[PendingReview] = []

        for field_name, field_info in fields_data.items():
            if isinstance(field_info, dict):
                value = field_info.get("value")
                confidence = float(field_info.get("confidence", field_info.get("confidence_score", 0.0)))
            else:
                value = field_info
                confidence = 0.0

            # Inclusive check: confidence >= threshold -> canonical record
            if confidence >= threshold:
                canonical_record_service.upsert_field(
                    document_id=document_id,
                    field_name=field_name,
                    value=value,
                    confidence=confidence,
                    db=db,
                )
                routed_to_canonical.append(field_name)
            else:
                # Below threshold -> route to pending_review queue
                val_str = json.dumps(value) if isinstance(value, (dict, list)) else (str(value) if value is not None else None)
                review_item = PendingReview(
                    id=str(uuid.uuid4()),
                    document_id=document_id,
                    field_name=field_name,
                    extracted_value=val_str,
                    confidence_score=confidence,
                    status=ReviewStatus.PENDING,
                    created_at=datetime.now(timezone.utc),
                )
                pending_records.append(review_item)
                routed_to_review.append(field_name)

        if pending_records:
            db.add_all(pending_records)
            db.commit()

        logger.info(
            f"[ConfidenceRouter] Routed document {document_id}: "
            f"{len(routed_to_canonical)} to canonical, {len(routed_to_review)} to review "
            f"(threshold={threshold:.2f})"
        )

        return RoutingResult(
            document_id=document_id,
            routed_to_canonical=routed_to_canonical,
            routed_to_review=routed_to_review,
            threshold_used=threshold,
        )
    except Exception as e:
        db.rollback()
        logger.error(f"[ConfidenceRouter] Routing failed for document {document_id}: {e}")
        raise e
    finally:
        if close_db:
            db.close()
