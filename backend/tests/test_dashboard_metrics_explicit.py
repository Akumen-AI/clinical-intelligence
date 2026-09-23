import pytest
import uuid
from datetime import datetime, timedelta
from app.models.user import User
from app.models.patient import Patient
from app.models.visit import Visit
from app.models.document import Document, DocumentStatus
from app.models.clinical_entities import Diagnosis, Medication
from app.models.extracted_field import ExtractedField
from app.services.dashboard_service import (
    get_admissions_metric,
    get_occupancy_metric,
    get_readmission_rate_metric,
    get_average_stay_metric,
    get_disease_distribution_metric,
)

@pytest.fixture
def dashboard_test_data(db_session):
    u_id = uuid.uuid4()
    p1_id = str(uuid.uuid4())
    p2_id = str(uuid.uuid4())
    doc1_id = str(uuid.uuid4())
    doc2_id = str(uuid.uuid4())
    doc3_id = str(uuid.uuid4())
    
    u = User(id=u_id, email="doc@test", role="doctor")
    p1 = Patient(patient_id=p1_id, name="P1")
    p2 = Patient(patient_id=p2_id, name="P2")
    db_session.add_all([u, p1, p2])
    db_session.flush()

    d1 = Document(document_id=doc1_id, patient_id=p1_id, filename="test1.pdf", raw_uri="s3://test/1.pdf", filetype="pdf", status=DocumentStatus.COMMITTED.value)
    d2 = Document(document_id=doc2_id, patient_id=p2_id, filename="test2.pdf", raw_uri="s3://test/2.pdf", filetype="pdf", status=DocumentStatus.COMMITTED.value)
    d3 = Document(document_id=doc3_id, patient_id=p1_id, filename="test3.pdf", raw_uri="s3://test/3.pdf", filetype="pdf", status=DocumentStatus.COMMITTED.value)
    db_session.add_all([d1, d2, d3])
    db_session.flush()

    now = datetime.utcnow()
    # P1 Visit 1: Admission, completed
    v1 = Visit(visit_id=str(uuid.uuid4()), patient_id=p1_id, document_id=doc1_id, department="Cardiology", visit_date=now - timedelta(days=40), admission_date=now - timedelta(days=40), discharge_date=now - timedelta(days=35))
    # P1 Visit 2: Readmitted 10 days later
    v2 = Visit(visit_id=str(uuid.uuid4()), patient_id=p1_id, document_id=doc3_id, department="Cardiology", visit_date=now - timedelta(days=25), admission_date=now - timedelta(days=25), discharge_date=now - timedelta(days=20))
    # P2 Visit 1: Active admission
    v3 = Visit(visit_id=str(uuid.uuid4()), patient_id=p2_id, document_id=doc2_id, department="Cardiology", visit_date=now - timedelta(days=2), admission_date=now - timedelta(days=2), discharge_date=None)
    db_session.add_all([v1, v2, v3])
    db_session.flush()

    ef1 = ExtractedField(field_id=str(uuid.uuid4()), document_id=doc1_id, field_name="diagnosis", raw_value="Hypertension", confidence_score=0.9, verification_status="auto_accepted")
    ef2 = ExtractedField(field_id=str(uuid.uuid4()), document_id=doc3_id, field_name="diagnosis", raw_value="Hypertension", confidence_score=0.9, verification_status="auto_accepted")
    db_session.add_all([ef1, ef2])
    db_session.flush()

    diag1 = Diagnosis(id=str(uuid.uuid4()), patient_id=p1_id, source_field_id=ef1.field_id, raw_text="Hypertension")
    diag2 = Diagnosis(id=str(uuid.uuid4()), patient_id=p1_id, source_field_id=ef2.field_id, raw_text="Hypertension")
    db_session.add_all([diag1, diag2])
    db_session.commit()

def test_occupancy_metric(db_session, dashboard_test_data):
    # Only P2 is actively admitted
    metric = get_occupancy_metric(db_session, "Cardiology", None, None)
    # Capacity is 50 for department
    assert metric["value"] == 2.0  # (1 active / 50) * 100
    assert metric["chart"][0]["value"] == 1  # 1 occupied

def test_readmission_rate_metric(db_session, dashboard_test_data):
    now_str = datetime.utcnow().isoformat()
    past_str = (datetime.utcnow() - timedelta(days=50)).isoformat()
    metric = get_readmission_rate_metric(db_session, "Cardiology", past_str, now_str)
    # V1 (p1) discharged 35 days ago, V2 (p1) admitted 25 days ago -> 10 days apart -> Readmission!
    # V2 (p1) discharged 20 days ago, no further admission.
    # Total discharges = 2 (v1, v2)
    # Readmissions = 1 (v1)
    assert metric["chart"][0]["value"] == 1  # 1 readmission
    assert metric["value"] == 50.0 # 1/2

def test_average_stay_metric(db_session, dashboard_test_data):
    metric = get_average_stay_metric(db_session, "Cardiology", None, None)
    # Discharges: v1 (5 days), v2 (5 days). v3 has no discharge.
    # Average = 5.0
    assert metric["value"] == 5.0

def test_disease_distribution_dedupes_patients(db_session, dashboard_test_data):
    metric = get_disease_distribution_metric(db_session, "Cardiology", None, None)
    # P1 has Hypertension twice (v1, v2), but distinct count of patients per disease should be 1.
    assert metric["value"] == 1
    assert metric["chart"][0]["count"] == 1
