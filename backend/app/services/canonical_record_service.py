import logging
import uuid
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.config import settings

from app.database import SessionLocal
from app.models.canonical_patient_record import CanonicalPatientRecord
from app.models.extracted_field import ExtractedField, VerificationStatus
from app.models.document import Document
from app.services import audit_service

logger = logging.getLogger("app.services.canonical_record_service")


class CanonicalWriteRejected(ValueError):
    """Raised when an extracted field has not passed verification."""


def route_to_normalized_tables(
    db: Session,
    patient_id: str,
    field_name: str,
    field_id: str,
    final_value: Any
):
    """Helper to route a structured value to its normalized clinical entity table."""
    if final_value and isinstance(final_value, list):
        if field_name == "medications":
            from app.models.clinical_entities import Medication
            from app.services.terminology_service import normalize_medication
            db.query(Medication).filter(Medication.source_field_id == field_id).delete()
            for item in final_value:
                if isinstance(item, dict):
                    raw_text = item.get("medication_name", str(item))
                    mapping = normalize_medication(raw_text)
                    db.add(Medication(
                        patient_id=patient_id,
                        source_field_id=field_id,
                        raw_text=raw_text,
                        rxnorm_code=mapping.code if mapping else None,
                        mapping_source=mapping.mapping_source if mapping else None,
                        mapping_version=mapping.mapping_version if mapping else None,
                        status="active"
                    ))
        elif field_name in ("diagnoses", "diagnosis"):
            from app.models.clinical_entities import Diagnosis
            from app.services.terminology_service import normalize_diagnosis
            db.query(Diagnosis).filter(Diagnosis.source_field_id == field_id).delete()
            for item in final_value:
                if isinstance(item, dict):
                    raw_text = item.get("condition_name", str(item))
                    mapping = normalize_diagnosis(raw_text)
                    db.add(Diagnosis(
                        patient_id=patient_id,
                        source_field_id=field_id,
                        raw_text=raw_text,
                        icd10_code=mapping.code if mapping else None,
                        mapping_source=mapping.mapping_source if mapping else None,
                        mapping_version=mapping.mapping_version if mapping else None,
                    ))
        elif field_name == "allergies":
            from app.models.clinical_entities import Allergy
            db.query(Allergy).filter(Allergy.source_field_id == field_id).delete()
            for item in final_value:
                if isinstance(item, dict):
                    db.add(Allergy(
                        patient_id=patient_id,
                        source_field_id=field_id,
                        raw_text=str(item),
                        allergen=item.get("allergen"),
                        reaction=item.get("reaction"),
                        severity=item.get("severity")
                    ))
        elif field_name == "lab_results":
            from app.models.clinical_entities import LabResult
            from app.models.canonical_patient_record import CanonicalPatientRecord
            db.query(LabResult).filter(LabResult.source_field_id == field_id).delete()
            
            # Find sibling document_date
            doc_date_record = db.query(CanonicalPatientRecord).filter(
                CanonicalPatientRecord.document_id == db.query(ExtractedField.document_id).filter(ExtractedField.field_id == field_id).scalar_subquery(),
                CanonicalPatientRecord.field_name == "document_date"
            ).first()
            recorded_at = doc_date_record.value if doc_date_record else None

            for item in final_value:
                if isinstance(item, dict):
                    import re
                    val_text = item.get("value")
                    val_num = None
                    if val_text:
                        num_match = re.search(r"[-+]?(?:\d*\.*\d+)", val_text)
                        if num_match:
                            try:
                                val_num = float(num_match.group(0))
                            except ValueError:
                                pass

                    db.add(LabResult(
                        patient_id=patient_id,
                        source_field_id=field_id,
                        raw_text=str(item),
                        test_name=item.get("test_name"),
                        value_text=val_text,
                        value_numeric=val_num,
                        unit=item.get("unit"),
                        reference_range=item.get("reference_range"),
                        flag=item.get("flag"),
                        recorded_at=str(recorded_at) if recorded_at else None
                    ))
        elif field_name == "procedures":
            from app.models.clinical_entities import Procedure
            db.query(Procedure).filter(Procedure.source_field_id == field_id).delete()
            for item in final_value:
                if isinstance(item, str):
                    db.add(Procedure(
                        patient_id=patient_id,
                        source_field_id=field_id,
                        raw_text=item
                    ))
    elif final_value and isinstance(final_value, dict):
        if field_name == "vitals":
            from app.models.clinical_entities import Vital
            db.query(Vital).filter(Vital.source_field_id == field_id).delete()
            for v_type, v_val in final_value.items():
                if v_val:
                    db.add(Vital(
                        patient_id=patient_id,
                        source_field_id=field_id,
                        raw_text=f"{v_type}: {v_val}",
                        type=v_type,
                        value=str(v_val)
                    ))

def write_field_to_canonical_record(
    field: ExtractedField,
    db: Session,
    value: Any = None,
    actor_user_id: Optional[uuid.UUID] = None,
) -> CanonicalPatientRecord:
    """The sole write boundary for extracted values entering the canonical record."""
    status = field.verification_status
    allowed = {VerificationStatus.AUTO_PASSED, VerificationStatus.HUMAN_VERIFIED}
    if status not in allowed:
        if status == "failed":
            reason = f"field status '{status}' is not writable"
        else:
            reason = f"confidence score below threshold; status '{status}' is not writable"
            
        logger.warning(
            "[CanonicalRecordService] Rejected canonical write: field_id=%s document_id=%s field_name=%s status=%s reason=%s",
            field.field_id,
            field.document_id,
            field.field_name,
            status,
            reason,
        )
        raise CanonicalWriteRejected(
            f"Canonical write rejected for field '{field.field_name}': {reason}"
        )

    doc = db.query(Document).filter(Document.document_id == field.document_id).first()
    patient_id = doc.patient_id if doc else None

    final_value = field.verified_value if value is None and field.verified_value is not None else (field.raw_value if value is None else value)

    # Fallback/un-normalized fields or if no patient is linked yet
    if not patient_id or field.field_name not in {"medications", "diagnoses", "diagnosis", "allergies", "lab_results", "vitals", "procedures"}:
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
                value=final_value,
                source_field_id=field.field_id,
            )
            db.add(canonical)
        else:
            canonical.value = final_value
            canonical.source_field_id = field.field_id

        db.commit()
        db.refresh(canonical)
        
        if actor_user_id:
            audit_service.write_entry(
                db=db,
                actor_user_id=actor_user_id,
                action_type="canonical_record_write",
                target_entity=f"canonical_record:{canonical.record_id}",
                rationale=f"Wrote field '{field.field_name}' to generic canonical record."
            )
            
        logger.info(
            "[CanonicalRecordService] Canonical write succeeded (generic): field_id=%s document_id=%s status=%s record_id=%s",
            field.field_id,
            field.document_id,
            status,
            canonical.record_id,
        )
        return canonical

    # Route to normalized entities
    route_to_normalized_tables(db, patient_id, field.field_name, field.field_id, final_value)

    db.commit()
    
    if actor_user_id:
        audit_service.write_entry(
            db=db,
            actor_user_id=actor_user_id,
            action_type="canonical_record_write",
            target_entity=f"canonical_record_normalized:{field.field_name}",
            rationale=f"Wrote field '{field.field_name}' to normalized clinical entities."
        )
        
    logger.info(
        "[CanonicalRecordService] Canonical write succeeded (normalized): field_id=%s document_id=%s field_name=%s",
        field.field_id,
        field.document_id,
        field.field_name,
    )
    return None


def upsert_field(
    document_id: str,
    field_name: str,
    value: Any,
    confidence: float,
    db: Optional[Session] = None,
    human_verified: bool = False,
    actor_user_id: Optional[uuid.UUID] = None,
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
            if human_verified:
                status = VerificationStatus.HUMAN_VERIFIED
            elif confidence >= settings.CONFIDENCE_THRESHOLD:
                status = VerificationStatus.AUTO_PASSED
            else:
                status = VerificationStatus.PENDING

            field = ExtractedField(
                document_id=document_id,
                field_name=field_name,
                raw_value=value,
                confidence_score=confidence,
                verification_status=status,
            )
            db.add(field)
            db.flush()
        elif human_verified:
            field.verified_value = value
            field.verification_status = VerificationStatus.HUMAN_VERIFIED
        else:
            if field.verification_status != "failed":
                if confidence >= settings.CONFIDENCE_THRESHOLD:
                    field.verification_status = VerificationStatus.AUTO_PASSED
                else:
                    field.verification_status = VerificationStatus.PENDING
        return write_field_to_canonical_record(field, db, value=value, actor_user_id=actor_user_id)
    except Exception:
        db.rollback()
        raise
    finally:
        if close_db:
            db.close()

def migrate_generic_records_to_normalized(document_id: str, patient_id: str, db: Session):
    """
    Migrates fields from the generic canonical_patient_records table to normalized
    clinical entity tables (e.g. medications, diagnoses) for a newly assigned patient.
    """
    records = db.query(CanonicalPatientRecord).filter(
        CanonicalPatientRecord.document_id == document_id
    ).all()

    for record in records:
        if record.field_name in {"medications", "diagnoses", "diagnosis", "allergies", "lab_results", "vitals", "procedures"}:
            route_to_normalized_tables(
                db=db,
                patient_id=patient_id,
                field_name=record.field_name,
                field_id=record.source_field_id,
                final_value=record.value,
            )
            logger.info(f"[CanonicalRecordService] Migrated generic record {record.field_name} to normalized table for patient {patient_id}")
    
    db.commit()
