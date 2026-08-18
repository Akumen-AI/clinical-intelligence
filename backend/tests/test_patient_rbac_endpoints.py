import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import date

from app.main import app
from app.models.patient import Patient
from app.models.document import Document
from app.models.user import User, UserRole
from tests.conftest import TestingSessionLocal

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def test_patient(db_session: Session):
    patient_id = str(uuid4())
    patient = Patient(
        patient_id=patient_id,
        patient_number=f"PT-TEST-{patient_id[:8]}",
        name="Test Patient RBAC",
        dob=date(1990, 1, 1),
        sex="M"
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return patient

@pytest.fixture
def test_document(db_session: Session, test_patient):
    doc_id = str(uuid4())
    doc = Document(
        document_id=doc_id,
        filename="test_doc.pdf",
        raw_uri="test_doc.pdf",
        filetype="application/pdf",
        patient_id=test_patient.patient_id,
        status="COMMITTED"
    )
    db_session.add(doc)
    db_session.commit()
    db_session.refresh(doc)
    return doc

def override_auth(role: UserRole, patient_access: list[str] = None):
    def _override():
        user = User(
            id=uuid4(),
            email=f"{role.value}@example.com",
            role=role,
            patient_access=patient_access or []
        )
        return user
    from app.core.security import get_current_user
    app.dependency_overrides[get_current_user] = _override

def clear_overrides():
    app.dependency_overrides.clear()

def test_doctor_denied_out_of_scope_patient(client: TestClient, test_patient):
    override_auth(UserRole.DOCTOR, patient_access=["other-patient-id"])
    
    # 1. GET /patients/{id}
    res = client.get(f"/api/v1/patients/{test_patient.patient_id}")
    assert res.status_code == 403
    
    # 2. GET /patients/{id}/records
    res = client.get(f"/api/v1/patients/{test_patient.patient_id}/records")
    assert res.status_code == 403

    clear_overrides()

def test_doctor_permitted_in_scope_patient(client: TestClient, test_patient):
    override_auth(UserRole.DOCTOR, patient_access=[test_patient.patient_id])
    
    res = client.get(f"/api/v1/patients/{test_patient.patient_id}")
    assert res.status_code == 200
    
    clear_overrides()

def test_hospital_admin_bypasses_restriction(client: TestClient, test_patient):
    override_auth(UserRole.HOSPITAL_ADMIN, patient_access=[])
    
    res = client.get(f"/api/v1/patients/{test_patient.patient_id}")
    assert res.status_code == 200
    
    clear_overrides()

def test_department_head_denied_direct_access(client: TestClient, test_patient):
    override_auth(UserRole.DEPARTMENT_HEAD)
    
    res = client.get(f"/api/v1/patients/{test_patient.patient_id}")
    assert res.status_code == 403
    
    clear_overrides()

def test_timeline_patient_id_required_for_doctor(client: TestClient, test_patient):
    override_auth(UserRole.DOCTOR, patient_access=[test_patient.patient_id])
    
    # Allowed if provided
    res = client.get(f"/api/v1/timeline?patient_id={test_patient.patient_id}")
    assert res.status_code == 200
    
    # Denied if not provided
    res = client.get("/api/v1/timeline")
    assert res.status_code == 403

    clear_overrides()

def test_timeline_event_document_scoped(client: TestClient, test_patient, test_document):
    override_auth(UserRole.DOCTOR, patient_access=["wrong-patient-id"])
    
    res = client.get(f"/api/v1/timeline/{test_document.document_id}")
    assert res.status_code == 403
    
    clear_overrides()

def test_review_pending_list_filtered(client: TestClient, test_patient, test_document):
    # For a doctor, if we don't pass document_id, it should filter to only their patients
    # We test it by ensuring it returns 200, we don't strictly test the DB result right now
    override_auth(UserRole.DOCTOR, patient_access=[])
    res = client.get("/api/v1/review/pending")
    assert res.status_code == 200
    assert len(res.json()["items"]) == 0  # should not see other patients' docs
    
    clear_overrides()
