import pytest
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentStatus
from app.models.patient import Patient
from app.models.user import User, UserRole
from app.models.extraction_run import ExtractionRun
from app.models.extracted_field import ExtractedField
from app.models.canonical_patient_record import CanonicalPatientRecord
from app.services.canonical_record_service import (
    route_to_normalized_tables,
    write_field_to_canonical_record
)

@pytest.fixture
def test_data(db_session: Session):
    patient_id = str(uuid.uuid4())
    patient = Patient(patient_id=patient_id, mrn="TEST1234", name="John Doe")
    
    user_id = uuid.uuid4()
    user = User(id=user_id, email="doctor@test.com", role=UserRole.DOCTOR, patient_access=[patient_id])
    
    doc_id = str(uuid.uuid4())
    doc = Document(
        document_id=doc_id,
        patient_id=patient_id,
        filename="test.pdf",
        raw_uri="s3://test/test.pdf",
        filetype="application/pdf",
        document_type="Lab Report",
        status=DocumentStatus.QUEUED.value
    )
    
    db_session.add_all([patient, user, doc])
    db_session.commit()
    
    return {
        "patient_id": patient_id,
        "user_id": user_id,
        "document_id": doc_id
    }

def test_extraction_run_creation(db_session: Session, test_data):
    doc_id = test_data["document_id"]
    
    run_id = str(uuid.uuid4())
    run = ExtractionRun(
        run_id=run_id,
        document_id=doc_id,
        extractor_name="test_extractor",
        extractor_version="1.0",
        status="processing"
    )
    db_session.add(run)
    db_session.commit()
    
    # Associate it with document
    doc = db_session.query(Document).filter_by(document_id=doc_id).first()
    doc.current_extraction_run_id = run_id
    doc.document_version = 1
    db_session.commit()
    
    fetched = db_session.query(ExtractionRun).filter_by(run_id=run_id).first()
    assert fetched is not None
    assert fetched.document_id == doc_id
    assert doc.current_extraction_run_id == run_id

def test_idempotent_extraction(db_session: Session, test_data):
    patient_id = test_data["patient_id"]
    doc_id = test_data["document_id"]
    
    # Run 1
    run1_id = str(uuid.uuid4())
    run1 = ExtractionRun(
        run_id=run1_id, document_id=doc_id, extractor_name="ex", extractor_version="1", 
        status="completed"
    )
    db_session.add(run1)
    
    field1 = ExtractedField(
        field_id=str(uuid.uuid4()),
        document_id=doc_id,
        extraction_run_id=run1_id,
        field_name="WBC",
        raw_value="10.5",
        confidence_score=0.9, verification_status="auto_passed"
    )
    db_session.add(field1)
    db_session.commit()
    
    write_field_to_canonical_record(field1, db_session)
    
    canonical_wbc = db_session.query(CanonicalPatientRecord).filter_by(document_id=doc_id, field_name="WBC").first()
    assert canonical_wbc.value == "10.5"
    assert canonical_wbc.source_field_id == field1.field_id
    
    # Run 2 (Reprocessing)
    run2_id = str(uuid.uuid4())
    run2 = ExtractionRun(
        run_id=run2_id, document_id=doc_id, extractor_name="ex", extractor_version="2", 
        status="completed"
    )
    run1.supersedes_run_id = run2_id
    db_session.add(run2)
    
    field2 = ExtractedField(
        field_id=str(uuid.uuid4()),
        document_id=doc_id,
        extraction_run_id=run2_id,
        field_name="WBC",
        raw_value="11.0",
        confidence_score=0.9, verification_status="auto_passed"
    )
    db_session.add(field2)
    db_session.commit()
    
    write_field_to_canonical_record(field2, db_session)
    
    # Old canonical record should be overwritten with new unverified run
    canonical_wbc = db_session.query(CanonicalPatientRecord).filter_by(document_id=doc_id, field_name="WBC").first()
    assert canonical_wbc.value == "11.0"
    assert canonical_wbc.source_field_id == field2.field_id
    
    # Old field should still exist (history preserved)
    all_fields = db_session.query(ExtractedField).filter_by(field_name="WBC").all()
    assert len(all_fields) == 2

def test_verification_gates_prevent_overwrite(db_session: Session, test_data):
    patient_id = test_data["patient_id"]
    doc_id = test_data["document_id"]
    
    run1_id = str(uuid.uuid4())
    run1 = ExtractionRun(run_id=run1_id, document_id=doc_id, extractor_name="ex", extractor_version="1", status="completed")
    db_session.add(run1)
    
    field1 = ExtractedField(field_id=str(uuid.uuid4()), document_id=doc_id, extraction_run_id=run1_id, field_name="RBC", raw_value="4.5", confidence_score=0.9, verification_status="auto_passed")
    db_session.add(field1)
    db_session.commit()
    
    write_field_to_canonical_record(field1, db_session)
    
    # Human verifies it
    canonical_rbc = db_session.query(CanonicalPatientRecord).filter_by(document_id=doc_id, field_name="RBC").first()
    source_field = db_session.query(ExtractedField).filter_by(field_id=canonical_rbc.source_field_id).first()
    source_field.verification_status = "human_verified"
    source_field.reviewer_id = str(test_data["user_id"])
    db_session.commit()
    
    # Run 2 tries to overwrite
    run2_id = str(uuid.uuid4())
    run2 = ExtractionRun(run_id=run2_id, document_id=doc_id, extractor_name="ex", extractor_version="2", status="completed")
    db_session.add(run2)
    
    field2 = ExtractedField(field_id=str(uuid.uuid4()), document_id=doc_id, extraction_run_id=run2_id, field_name="RBC", raw_value="5.0", confidence_score=0.9, verification_status="auto_passed")
    db_session.add(field2)
    db_session.commit()
    
    # Should not overwrite because it's human verified
    write_field_to_canonical_record(field2, db_session)
    
    canonical_rbc = db_session.query(CanonicalPatientRecord).filter_by(document_id=doc_id, field_name="RBC").first()
    source_field = db_session.query(ExtractedField).filter_by(field_id=canonical_rbc.source_field_id).first()
    assert canonical_rbc.value == "4.5"
    assert canonical_rbc.source_field_id == field1.field_id
    assert source_field.verification_status == "human_verified"
