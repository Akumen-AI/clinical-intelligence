import uuid
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.patient import Patient
from app.models.extracted_field import ExtractedField, VerificationStatus
from app.models.clinical_entities import Diagnosis
from app.services.canonical_record_service import write_field_to_canonical_record

from tests.conftest import TestingSessionLocal

def test_diagnosis_singular_routing():
    db = TestingSessionLocal()
    patient_id = str(uuid.uuid4())
    patient = Patient(patient_id=patient_id, name="Test Patient")
    db.add(patient)
    
    doc_id = str(uuid.uuid4())
    doc = Document(document_id=doc_id, patient_id=patient_id, status="extracted", filename="test.pdf", raw_uri="test.pdf", filetype="application/pdf")
    db.add(doc)
    
    field_id = str(uuid.uuid4())
    field = ExtractedField(
        field_id=field_id,
        document_id=doc_id,
        field_name="diagnosis",  # singular, as requested
        verification_status=VerificationStatus.AUTO_PASSED,
        raw_value=[{"condition_name": "Asthma", "icd10_code": "J45.909", "snomed_code": "195967001"}],
        confidence_score=0.9
    )
    db.add(field)
    db.commit()
    
    # Call the service method
    write_field_to_canonical_record(field, db)
    
    # Verify it ended up in Diagnosis table
    diagnoses = db.query(Diagnosis).filter(Diagnosis.patient_id == patient_id).all()
    assert len(diagnoses) == 1
    assert diagnoses[0].raw_text == "Asthma"
    assert diagnoses[0].icd10_code == "J45.909"
    assert diagnoses[0].snomed_code == "195967001"
    assert diagnoses[0].source_field_id == field_id

def test_medication_routing():
    db = TestingSessionLocal()
    patient_id = str(uuid.uuid4())
    patient = Patient(patient_id=patient_id, name="Test Patient")
    db.add(patient)
    
    doc_id = str(uuid.uuid4())
    doc = Document(document_id=doc_id, patient_id=patient_id, status="extracted", filename="test.pdf", raw_uri="test.pdf", filetype="application/pdf")
    db.add(doc)
    
    field_id = str(uuid.uuid4())
    field = ExtractedField(
        field_id=field_id,
        document_id=doc_id,
        field_name="medications",
        verification_status=VerificationStatus.AUTO_PASSED,
        raw_value=[{"medication_name": "Lisinopril", "rxnorm_code": "197361"}],
        confidence_score=0.9
    )
    db.add(field)
    db.commit()
    
    write_field_to_canonical_record(field, db)
    
    from app.models.clinical_entities import Medication
    meds = db.query(Medication).filter(Medication.patient_id == patient_id).all()
    assert len(meds) == 1
    assert meds[0].raw_text == "Lisinopril"
    assert meds[0].rxnorm_code == "197361"
    assert meds[0].source_field_id == field_id

def test_lab_result_routing():
    db = TestingSessionLocal()
    patient_id = str(uuid.uuid4())
    patient = Patient(patient_id=patient_id, name="Test Patient")
    db.add(patient)
    
    doc_id = str(uuid.uuid4())
    doc = Document(document_id=doc_id, patient_id=patient_id, status="extracted", filename="test.pdf", raw_uri="test.pdf", filetype="application/pdf")
    db.add(doc)
    
    field_id = str(uuid.uuid4())
    field = ExtractedField(
        field_id=field_id,
        document_id=doc_id,
        field_name="lab_results",
        verification_status=VerificationStatus.AUTO_PASSED,
        raw_value=[{"test_name": "Hemoglobin", "loinc_code": "718-7", "value": "14.5"}],
        confidence_score=0.9
    )
    db.add(field)
    db.commit()
    
    write_field_to_canonical_record(field, db)
    
    from app.models.clinical_entities import LabResult
    labs = db.query(LabResult).filter(LabResult.patient_id == patient_id).all()
    assert len(labs) == 1
    assert labs[0].test_name == "Hemoglobin"
    assert labs[0].loinc_code == "718-7"
    assert labs[0].source_field_id == field_id
