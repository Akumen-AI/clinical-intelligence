import time
import pytest
from uuid import uuid4
from datetime import date, datetime
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.main import app
from app.models.patient import Patient
from app.models.document import Document
from app.models.clinical_entities import LabResult, Medication, Diagnosis
from app.models.extracted_field import ExtractedField
from app.models.canonical_patient_record import CanonicalPatientRecord
from app.models.user import UserRole
from tests.test_patient_rbac_endpoints import get_auth_client, db_session, test_patient

def test_dashboard_success_and_grouping(db_session: Session, test_patient):
    # Setup data
    doc_id = str(uuid4())
    doc = Document(
        document_id=doc_id, patient_id=test_patient.patient_id, status="committed",
        filename="test.pdf", raw_uri="test.pdf", filetype="application/pdf"
    )
    db_session.add(doc)
    
    # Active med
    med1 = Medication(
        id=str(uuid4()), patient_id=test_patient.patient_id,
        raw_text="Aspirin", status="active", source_field_id="none1"
    )
    # Discontinued med
    med2 = Medication(
        id=str(uuid4()), patient_id=test_patient.patient_id,
        raw_text="Tylenol", status="discontinued", source_field_id="none2"
    )
    db_session.add_all([med1, med2])

    # Numeric Labs
    lab1 = LabResult(
        id=str(uuid4()), patient_id=test_patient.patient_id, test_name="Glucose",
        value_numeric=100.5, recorded_at="2023-01-01", source_field_id="none3",
        raw_text="Glucose: 100.5"
    )
    lab2 = LabResult(
        id=str(uuid4()), patient_id=test_patient.patient_id, test_name="Glucose",
        value_numeric=110.0, recorded_at="2023-01-02", source_field_id="none4",
        raw_text="Glucose: 110.0"
    )
    # Non-numeric Lab
    lab3 = LabResult(
        id=str(uuid4()), patient_id=test_patient.patient_id, test_name="Blood Type",
        value_numeric=None, value_text="O+", source_field_id="none5",
        raw_text="Blood Type O+"
    )
    db_session.add_all([lab1, lab2, lab3])
    db_session.commit()

    client = get_auth_client(db_session, UserRole.DOCTOR, patient_access=[test_patient.patient_id])
    res = client.get(f"/api/v1/dashboards/patient/{test_patient.patient_id}")
    
    assert res.status_code == 200
    data = res.json()
    
    # Check meds
    meds = data["current_medications"]
    assert len(meds) == 1
    assert meds[0]["raw_text"] == "Aspirin"
    
    # Check labs
    trends = data["lab_trends"]
    assert "Glucose" in trends
    assert len(trends["Glucose"]) == 2
    assert trends["Glucose"][0]["value"] == 100.5
    assert trends["Glucose"][1]["value"] == 110.0
    
    other_labs = data["other_lab_results"]
    assert len(other_labs) == 1
    assert other_labs[0]["test_name"] == "Blood Type"

def test_dashboard_rbac_role_denied(db_session: Session, test_patient):
    # Nurse is not in the allowed set {DOCTOR, HOSPITAL_ADMIN}
    client = get_auth_client(db_session, UserRole.NURSE, patient_access=[test_patient.patient_id])
    res = client.get(f"/api/v1/dashboards/patient/{test_patient.patient_id}")
    assert res.status_code == 403

def test_dashboard_rbac_patient_denied(db_session: Session, test_patient):
    # Doctor doesn't have access to this patient
    client = get_auth_client(db_session, UserRole.DOCTOR, patient_access=["some-other-id"])
    res = client.get(f"/api/v1/dashboards/patient/{test_patient.patient_id}")
    assert res.status_code == 403

def test_dashboard_performance(db_session: Session, test_patient):
    # Add ~50 numeric labs and ~30 timeline events (docs, diagnoses, etc.)
    docs = []
    for i in range(30):
        doc_id = str(uuid4())
        doc = Document(
            document_id=doc_id, patient_id=test_patient.patient_id, status="committed",
            filename=f"test_{i}.pdf", raw_uri=f"test_{i}.pdf", filetype="application/pdf"
        )
        docs.append(doc)
        
        field_id = str(uuid4())
        field = ExtractedField(
            field_id=field_id, document_id=doc_id, field_name="document_date",
            verification_status="auto_passed", confidence_score=0.9
        )
        db_session.add(field)
        
        record = CanonicalPatientRecord(
            document_id=doc_id, field_name="document_date",
            value="2023-01-01", source_field_id=field_id
        )
        db_session.add(record)
    db_session.add_all(docs)
    
    labs = []
    for i in range(50):
        labs.append(LabResult(
            id=str(uuid4()), patient_id=test_patient.patient_id, test_name=f"Test_{i%5}",
            value_numeric=10.0 + i, recorded_at=f"2023-01-{1+i%28:02d}", source_field_id=f"none{i}",
            raw_text=f"Test_{i%5} {10.0 + i}"
        ))
    db_session.add_all(labs)
    db_session.commit()

    client = get_auth_client(db_session, UserRole.HOSPITAL_ADMIN)
    
    start_time = time.perf_counter()
    res = client.get(f"/api/v1/dashboards/patient/{test_patient.patient_id}")
    duration = time.perf_counter() - start_time
    
    assert res.status_code == 200
    assert duration < 2.0  # Must respond in under 2 seconds
    data = res.json()
    assert data["total_events"] >= 30
