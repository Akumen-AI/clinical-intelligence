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
from app.core.security import get_password_hash, create_access_token

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def test_patients(db_session: Session):
    p1_id = str(uuid4())
    p2_id = str(uuid4())
    
    p1 = Patient(patient_id=p1_id, patient_number="PT-1", name="Patient One", dob=date(1990, 1, 1), sex="M")
    p2 = Patient(patient_id=p2_id, patient_number="PT-2", name="Patient Two", dob=date(1980, 2, 2), sex="F")
    
    db_session.add(p1)
    db_session.add(p2)
    db_session.commit()
    
    return {"p1": p1_id, "p2": p2_id}

@pytest.fixture
def test_documents(db_session: Session, test_patients):
    d1_id = str(uuid4())
    d2_id = str(uuid4())
    
    d1 = Document(
        document_id=d1_id,
        filename="doc1.pdf",
        raw_uri="doc1.pdf",
        filetype="application/pdf",
        patient_id=test_patients["p1"],
        status="COMMITTED"
    )
    d2 = Document(
        document_id=d2_id,
        filename="doc2.pdf",
        raw_uri="doc2.pdf",
        filetype="application/pdf",
        patient_id=test_patients["p2"],
        status="COMMITTED"
    )
    
    db_session.add(d1)
    db_session.add(d2)
    db_session.commit()
    
    return {"d1": d1_id, "d2": d2_id}

def get_client_for_patient(db_session, patient_id):
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"{user_id}@test.clinic.org",
        role=UserRole.DOCTOR,
        patient_access=[patient_id],
        password_hash=get_password_hash("password")
    )
    db_session.add(user)
    db_session.commit()
    
    token = create_access_token(data={"sub": str(user_id), "role": "doctor", "email": user.email, "patient_access": [patient_id]})
    c = TestClient(app, base_url="https://testserver")
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c

def test_document_get_isolation(db_session, test_patients, test_documents):
    # Doctor has access to p1 only
    client = get_client_for_patient(db_session, test_patients["p1"])
    
    # Can access doc 1
    resp = client.get(f"/api/v1/documents/{test_documents['d1']}")
    assert resp.status_code == 200
    
    # Cannot access doc 2
    resp = client.get(f"/api/v1/documents/{test_documents['d2']}")
    assert resp.status_code == 403

def test_document_list_filtered(db_session, test_patients, test_documents):
    client = get_client_for_patient(db_session, test_patients["p1"])
    
    resp = client.get("/api/v1/documents")
    assert resp.status_code == 200
    
    docs = resp.json()
    # List should only contain doc 1, not doc 2
    assert len(docs) > 0
    for d in docs:
        assert d["document_id"] != test_documents["d2"]
        
def test_document_status_isolation(db_session, test_patients, test_documents):
    client = get_client_for_patient(db_session, test_patients["p1"])
    
    resp = client.get(f"/api/v1/documents/{test_documents['d2']}/status")
    assert resp.status_code == 403
    
def test_document_delete_isolation(db_session, test_patients, test_documents):
    client = get_client_for_patient(db_session, test_patients["p1"])
    
    resp = client.delete(f"/api/v1/documents/{test_documents['d2']}")
    assert resp.status_code == 403
