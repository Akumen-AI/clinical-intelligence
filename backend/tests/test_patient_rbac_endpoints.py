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
from app.core.security import get_password_hash

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

def get_auth_client(db_session: Session, role: UserRole, patient_access: list[str] = None):
    email = f"{uuid4()}@example.com"
    password = "testpassword123"
    user = User(
        id=uuid4(),
        email=email,
        password_hash=get_password_hash(password),
        role=role,
        patient_access=patient_access or []
    )
    db_session.add(user)
    db_session.commit()
    
    unauthed_client = TestClient(app)
    res = unauthed_client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    token = res.json()["access_token"]
    
    new_client = TestClient(app)
    new_client.headers.update({"Authorization": f"Bearer {token}"})
    return new_client


def test_doctor_denied_out_of_scope_patient(db_session: Session, test_patient):
    client = get_auth_client(db_session, UserRole.DOCTOR, patient_access=["other-patient-id"])
    
    # 1. GET /patients/{id}
    res = client.get(f"/api/v1/patients/{test_patient.patient_id}")
    assert res.status_code == 403
    
    # 2. GET /patients/{id}/records
    res = client.get(f"/api/v1/patients/{test_patient.patient_id}/records")
    assert res.status_code == 403
    
    # 3. POST /patients/{id}/ask
    res = client.post(f"/api/v1/patients/{test_patient.patient_id}/ask", json={"question": "What is the diagnosis?"})
    assert res.status_code == 403

def test_doctor_permitted_in_scope_patient(db_session: Session, test_patient):
    client = get_auth_client(db_session, UserRole.DOCTOR, patient_access=[test_patient.patient_id])
    
    res = client.get(f"/api/v1/patients/{test_patient.patient_id}")
    assert res.status_code == 200

def test_hospital_admin_bypasses_restriction(db_session: Session, test_patient):
    client = get_auth_client(db_session, UserRole.HOSPITAL_ADMIN, patient_access=[])
    
    res = client.get(f"/api/v1/patients/{test_patient.patient_id}")
    assert res.status_code == 200

def test_department_head_denied_direct_access(db_session: Session, test_patient):
    client = get_auth_client(db_session, UserRole.DEPARTMENT_HEAD)
    
    res = client.get(f"/api/v1/patients/{test_patient.patient_id}")
    assert res.status_code == 403

def test_timeline_patient_id_required_for_doctor(db_session: Session, test_patient):
    client = get_auth_client(db_session, UserRole.DOCTOR, patient_access=[test_patient.patient_id])
    
    # Allowed if provided
    res = client.get(f"/api/v1/timeline?patient_id={test_patient.patient_id}")
    assert res.status_code == 200
    
    # Denied if not provided
    res = client.get("/api/v1/timeline")
    assert res.status_code == 403

def test_timeline_event_document_scoped(db_session: Session, test_patient, test_document):
    client = get_auth_client(db_session, UserRole.DOCTOR, patient_access=["wrong-patient-id"])
    
    res = client.get(f"/api/v1/timeline/{test_document.document_id}")
    assert res.status_code == 403

def test_review_pending_list_filtered(db_session: Session, test_patient, test_document):
    client = get_auth_client(db_session, UserRole.DOCTOR, patient_access=[])
    res = client.get("/api/v1/review/pending")
    assert res.status_code == 200
    assert len(res.json()["items"]) == 0

def test_correction_submitting_routes_denied_for_doctor(db_session: Session, test_patient, test_document):
    client = get_auth_client(db_session, UserRole.DOCTOR, patient_access=[test_patient.patient_id])
    
    # Allowed GETs
    res_layout = client.get(f"/api/v1/documents/{test_document.document_id}/layout")
    assert res_layout.status_code != 403  # May be 404 if data doesn't exist, but not 403

    # Denied POST/PATCH
    res_fields = client.post(f"/api/v1/documents/{test_document.document_id}/extract")
    assert res_fields.status_code == 403
    
    res_review = client.patch(f"/api/v1/review/pending/some-review-id", json={"status": "APPROVED"})
    assert res_review.status_code == 403

def test_correction_submitting_routes_denied_for_hospital_admin(db_session: Session, test_patient, test_document):
    client = get_auth_client(db_session, UserRole.HOSPITAL_ADMIN, patient_access=[])
    
    # Allowed GETs
    res_layout = client.get(f"/api/v1/documents/{test_document.document_id}/layout")
    assert res_layout.status_code != 403
    
    res_fields = client.post(f"/api/v1/documents/{test_document.document_id}/extract")
    assert res_fields.status_code == 403
    
    res_review = client.patch(f"/api/v1/review/pending/some-review-id", json={"status": "APPROVED"})
    assert res_review.status_code == 403
    
    # Allowed PUT config
    res_config = client.put("/api/v1/review/config/threshold", json={"threshold": 0.95})
    assert res_config.status_code != 403

def test_notes_endpoints_denied_for_it(client_as):
    client = client_as("it")
    assert client.post("/api/v1/notes", json={"patient_id": "123", "content": "hello"}).status_code == 403
    assert client.get("/api/v1/notes/123").status_code == 403

def test_notes_post_denied_for_department_head(client_as):
    client = client_as("department_head")
    assert client.post("/api/v1/notes", json={"patient_id": "123", "content": "hello"}).status_code == 403
