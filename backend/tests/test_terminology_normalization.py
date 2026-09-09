import uuid

from app.models.clinical_entities import Diagnosis, Medication
from app.models.document import Document
from app.models.extracted_field import ExtractedField, VerificationStatus
from app.services.canonical_record_service import write_field_to_canonical_record
from app.services.terminology_service import normalize_diagnosis, normalize_medication
from tests.conftest import TestingSessionLocal


def _verified_field(db, patient_id, field_name, value):
    document = Document(
        document_id=str(uuid.uuid4()),
        patient_id=patient_id,
        status="extracted",
        filename="terminology.pdf",
        raw_uri="terminology.pdf",
        filetype="application/pdf",
    )
    field = ExtractedField(
        field_id=str(uuid.uuid4()),
        document_id=document.document_id,
        field_name=field_name,
        raw_value=value,
        verified_value=value,
        confidence_score=1.0,
        verification_status=VerificationStatus.HUMAN_VERIFIED,
    )
    db.add_all([document, field])
    db.commit()
    return field


def test_known_medication_is_normalized_with_audit_metadata():
    mapping = normalize_medication("  METFORMIN  ")
    assert mapping.code == "6809"
    assert mapping.vocabulary == "RXNORM"
    assert mapping.mapping_source == "demo-subset"
    assert mapping.mapping_version == "v1"


def test_known_diagnosis_is_normalized_and_upstream_hint_is_not_used():
    mapping = normalize_diagnosis("Type 2 diabetes mellitus")
    assert mapping.code == "E11.9"
    assert mapping.vocabulary == "ICD10"

    db = TestingSessionLocal()
    patient_id = str(uuid.uuid4())
    from app.models.patient import Patient
    db.add(Patient(patient_id=patient_id, name="Terminology Test"))
    db.commit()
    field = _verified_field(
        db,
        patient_id,
        "diagnoses",
        [{"condition_name": "Type 2 diabetes mellitus", "icd10_code": "WRONG"}],
    )
    write_field_to_canonical_record(field, db)
    diagnosis = db.query(Diagnosis).filter(Diagnosis.source_field_id == field.field_id).one()
    assert diagnosis.icd10_code == "E11.9"
    assert diagnosis.mapping_source == "demo-subset"
    assert diagnosis.mapping_version == "v1"


def test_unmapped_term_is_saved_unchanged_without_code():
    db = TestingSessionLocal()
    patient_id = str(uuid.uuid4())
    from app.models.patient import Patient
    db.add(Patient(patient_id=patient_id, name="Terminology Test"))
    db.commit()
    raw_text = "Rare medication with punctuation (XR)"
    field = _verified_field(db, patient_id, "medications", [{"medication_name": raw_text}])
    write_field_to_canonical_record(field, db)
    medication = db.query(Medication).filter(Medication.source_field_id == field.field_id).one()
    assert medication.raw_text == raw_text
    assert medication.rxnorm_code is None
    assert medication.mapping_source is None
    assert medication.mapping_version is None


def test_rerouting_same_field_is_idempotent():
    db = TestingSessionLocal()
    patient_id = str(uuid.uuid4())
    from app.models.patient import Patient
    db.add(Patient(patient_id=patient_id, name="Terminology Test"))
    db.commit()
    field = _verified_field(db, patient_id, "medications", [{"medication_name": "lisinopril"}])
    write_field_to_canonical_record(field, db)
    first = db.query(Medication).filter(Medication.source_field_id == field.field_id).one()
    first_values = (first.raw_text, first.rxnorm_code, first.mapping_source, first.mapping_version)
    write_field_to_canonical_record(field, db)
    rows = db.query(Medication).filter(Medication.source_field_id == field.field_id).all()
    assert len(rows) == 1
    assert (rows[0].raw_text, rows[0].rxnorm_code, rows[0].mapping_source, rows[0].mapping_version) == first_values
