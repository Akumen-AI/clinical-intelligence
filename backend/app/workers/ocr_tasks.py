import os
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.extraction_field import ExtractionField
from app.services.confidence_service import aggregate_field_confidence, get_field_status


def extract_fields_task(
    document_id: str,
    image_path: Optional[str] = None,
    fields_config: Optional[List[Dict[str, Any]]] = None,
    paddle_results: Optional[Any] = None,
    db: Optional[Session] = None
) -> List[Dict[str, Any]]:
    """
    Celery / worker task to run PaddleOCR field extraction, calculate per-field
    confidence scores, assign statuses based on CONFIDENCE_THRESHOLD, and persist
    to the extraction_fields table.

    Args:
        document_id: ID of the document being processed.
        image_path: Path to the document image file.
        fields_config: List of dicts describing fields to extract, e.g.
            [{"field_name": "patient_id", "bounding_box": [...], "raw_value": "..."}, ...]
        paddle_results: OCR results structure (if already computed or mocked).
        db: Optional SQLAlchemy Session. If not provided, a new session is created.

    Returns:
        List of dicts representing extracted field records with confidence and status.
    """
    should_close_db = False
    if db is None:
        db = SessionLocal()
        should_close_db = True

    try:
        if not fields_config:
            # Default fallback sample field if none provided
            fields_config = [
                {
                    "field_name": "unknown_field",
                    "raw_value": None,
                    "bounding_box": None,
                }
            ]

        results = []
        for config in fields_config:
            field_name = config.get("field_name", "unnamed_field")
            bbox = config.get("bounding_box")
            field_ocr_data = config.get("paddle_result", paddle_results)
            provided_conf = config.get("confidence")

            # Calculate confidence using service if not explicitly supplied
            if provided_conf is not None:
                confidence = float(provided_conf)
            elif field_ocr_data is not None:
                confidence = aggregate_field_confidence(field_ocr_data, bbox)
            elif config.get("char_confidences"):
                confidence = aggregate_field_confidence(config.get("char_confidences"), bbox)
            else:
                confidence = 0.0

            raw_value = config.get("raw_value")
            status = get_field_status(confidence, raw_value)

            field_record = ExtractionField(
                field_id=config.get("field_id", str(uuid.uuid4())),
                document_id=document_id,
                field_name=field_name,
                raw_value=raw_value,
                confidence=confidence,
                status=status,
                bounding_box=bbox
            )

            db.add(field_record)
            results.append({
                "field_id": field_record.field_id,
                "document_id": document_id,
                "field_name": field_name,
                "raw_value": raw_value,
                "confidence": confidence,
                "status": status,
                "bounding_box": bbox
            })

        db.commit()
        return results

    except Exception:
        db.rollback()
        raise
    finally:
        if should_close_db:
            db.close()
