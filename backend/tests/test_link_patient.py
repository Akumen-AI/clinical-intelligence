import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from tests.conftest import TestingSessionLocal
from app.models.document import Document
from app.models.extracted_field import ExtractedField, VerificationStatus
from app.models.canonical_patient_record import CanonicalPatientRecord
from app.models.clinical_entities import Diagnosis
from app.models.visit import Visit
from app.services.canonical_record_service import write_field_to_canonical_record

client = TestClient(app)

def test_link_patient_migrates_flat_records_and_creates_visit():
    db = TestingSessionLocal()
    try:
        # Setup: Unlinked document
        doc_id = str(uuid.uuid4())
        doc = Document(
            document_id=doc_id,
            filename="test_migr.pdf",
            raw_uri="uploads/test_migr.pdf",
            filetype="pdf",
            status="extracted"
        )
        db.add(doc)
        db.commit()

        # Setup: Verify a field on unlinked document
        field_id = str(uuid.uuid4())
        field = ExtractedField(
            field_id=field_id,
            document_id=doc_id,
            field_name="diagnoses",
            raw_value=[{"condition_name": "Asthma", "icd10_code": "J45.9"}],
            verified_value=[{"condition_name": "Asthma", "icd10_code": "J45.9"}],
            confidence_score=0.9,
            verification_status=VerificationStatus.HUMAN_VERIFIED
        )
        db.add(field)
        db.commit()

        # Write to canonical record
        write_field_to_canonical_record(field, db)
        
        # Verify it landed in flat table
        flat_records = db.query(CanonicalPatientRecord).filter(
            CanonicalPatientRecord.document_id == doc_id
        ).all()
        assert len(flat_records) == 1
        assert flat_records[0].field_name == "diagnoses"

        # Verify no normalized rows yet
        diagnoses = db.query(Diagnosis).filter(Diagnosis.source_field_id == field_id).all()
        assert len(diagnoses) == 0

        # Action: Link document to new patient
        mrn = "MRN-LINK-TEST"
        resp = client.post(f"/api/v1/documents/{doc_id}/link-patient", json={
            "create_new": True,
            "mrn": mrn,
            "name": "Jane Doe Migr",
            "dob": "1980-05-15",
            "sex": "Female"
        })
        assert resp.status_code == 200
        patient_id = resp.json()["patient_id"]

        # Verify: Gone from flat table
        flat_records_after = db.query(CanonicalPatientRecord).filter(
            CanonicalPatientRecord.document_id == doc_id
        ).all()
        assert len(flat_records_after) == 0

        # Verify: Present in normalized table
        diagnoses_after = db.query(Diagnosis).filter(Diagnosis.source_field_id == field_id).all()
        assert len(diagnoses_after) == 1
        assert diagnoses_after[0].patient_id == patient_id
        assert diagnoses_after[0].raw_text == "Asthma"
        assert diagnoses_after[0].icd10_code == "J45.9"

        # Verify: Visit row created
        visit = db.query(Visit).filter(Visit.document_id == doc_id).first()
        assert visit is not None
        assert visit.patient_id == patient_id
        assert visit.visit_date is not None

    finally:
        db.close()
