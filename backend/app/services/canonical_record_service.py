import logging
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.canonical_patient_record import CanonicalPatientRecord
from app.models.extracted_field import ExtractedField, VerificationStatus

logger = logging.getLogger("app.services.canonical_record_service")


class CanonicalWriteRejected(ValueError):
    """Raised when an extracted field has not passed verification."""


def write_field_to_canonical_record(
    field: ExtractedField,
    db: Session,
    value: Any = None,
) -> CanonicalPatientRecord:
    """The sole write boundary for extracted values entering the canonical record."""
    status = field.verification_status
    allowed = {VerificationStatus.AUTO_PASSED, VerificationStatus.HUMAN_VERIFIED}
    if status not in allowed:
        reason = f"verification status '{status}' is not allowed; required auto_passed or human_verified"
        logger.warning(
            "[CanonicalRecordService] Rejected canonical write: field_id=%s document_id=%s status=%s reason=%s",
            field.field_id,
            field.document_id,
            status,
            reason,
        )
        raise CanonicalWriteRejected(
            f"Canonical write rejected for field '{field.field_name}': {reason}"
        )

    canonical = (
        db.query(CanonicalPatientRecord)
        .filter(
            CanonicalPatientRecord.document_id == field.document_id,
            CanonicalPatientRecord.field_name == field.field_name,
        )
        .first()
    )
    if canonical is None:
        canonical = CanonicalPatientRecord(
            document_id=field.document_id,
            field_name=field.field_name,
            value=field.verified_value if value is None and field.verified_value is not None else (field.raw_value if value is None else value),
            source_field_id=field.field_id,
        )
        db.add(canonical)
    else:
        canonical.value = field.verified_value if value is None and field.verified_value is not None else (field.raw_value if value is None else value)
        canonical.source_field_id = field.field_id

    db.commit()
    db.refresh(canonical)
    logger.info(
        "[CanonicalRecordService] Canonical write succeeded: field_id=%s document_id=%s status=%s record_id=%s",
        field.field_id,
        field.document_id,
        status,
        canonical.record_id,
    )
    return canonical


def upsert_field(
    document_id: str,
    field_name: str,
    value: Any,
    confidence: float,
    db: Optional[Session] = None,
    human_verified: bool = False,
) -> CanonicalPatientRecord:
    """Compatibility adapter; all persistence delegates to the verification gate."""
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True
    try:
        field = (
            db.query(ExtractedField)
            .filter(ExtractedField.document_id == document_id, ExtractedField.field_name == field_name)
            .first()
        )
        if field is None:
            field = ExtractedField(
                document_id=document_id,
                field_name=field_name,
                raw_value=value,
                confidence_score=confidence,
                verification_status=VerificationStatus.HUMAN_VERIFIED if human_verified else VerificationStatus.AUTO_PASSED,
            )
            db.add(field)
            db.flush()
        elif human_verified:
            field.verified_value = value
            field.verification_status = VerificationStatus.HUMAN_VERIFIED
        return write_field_to_canonical_record(field, db, value=value)
    except Exception:
        db.rollback()
        raise
    finally:
        if close_db:
            db.close()
