import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime, timezone

from app.main import app
from app.models.document import Document
from app.models.pending_review import PendingReview, ReviewStatus
from tests.conftest import TestingSessionLocal
from app.models.user import User, UserRole
from app.core.security import get_password_hash, create_access_token

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_auth_client(db_session, role, patient_access=None):
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"{user_id}@test.clinic.org",
        role=role,
        patient_access=patient_access or [],
        password_hash=get_password_hash("password")
    )
    db_session.add(user)
    db_session.commit()
    
    token = create_access_token(data={"sub": str(user_id), "role": role.value, "email": user.email, "patient_access": patient_access or []})
    c = TestClient(app, base_url="https://testserver")
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c

def test_review_write_gate_locks_approved_reviews(db_session: Session):
    doc_id = str(uuid4())
    doc = Document(
        document_id=doc_id,
        filename="test.pdf",
        raw_uri="test.pdf",
        filetype="application/pdf",
        patient_id=None,
        status="COMMITTED"
    )
    db_session.add(doc)
    
    review_id = str(uuid4())
    review = PendingReview(
        id=review_id,
        document_id=doc_id,
        field_name="patient_name",
        extracted_value="John Doe",
        confidence_score=0.5,
        status=ReviewStatus.PENDING,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(review)
    db_session.commit()
    
    client = get_auth_client(db_session, UserRole.NURSE) # unlinked document, nurse has access
    
    # 1. Approve it
    resp = client.patch(f"/api/v1/review/pending/{review_id}", json={"action": "approve"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "APPROVED"
    
    # 2. Try to approve it again, should hit the write-gate
    resp2 = client.patch(f"/api/v1/review/pending/{review_id}", json={"action": "approve"})
    assert resp2.status_code == 400
    assert "Only PENDING reviews can be modified" in resp2.json()["detail"]
    
    # 3. Try to reject it now, should also fail
    resp3 = client.patch(f"/api/v1/review/pending/{review_id}", json={"action": "reject"})
    assert resp3.status_code == 400
    assert "Only PENDING reviews can be modified" in resp3.json()["detail"]

def test_review_write_gate_locks_rejected_reviews(db_session: Session):
    doc_id = str(uuid4())
    doc = Document(
        document_id=doc_id,
        filename="test.pdf",
        raw_uri="test.pdf",
        filetype="application/pdf",
        patient_id=None,
        status="COMMITTED"
    )
    db_session.add(doc)
    
    review_id = str(uuid4())
    review = PendingReview(
        id=review_id,
        document_id=doc_id,
        field_name="dob",
        extracted_value="invalid",
        confidence_score=0.1,
        status=ReviewStatus.PENDING,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(review)
    db_session.commit()
    
    client = get_auth_client(db_session, UserRole.NURSE)
    
    # 1. Reject it
    resp = client.patch(f"/api/v1/review/pending/{review_id}", json={"action": "reject"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "REJECTED"
    
    # 2. Try to modify it
    resp2 = client.patch(f"/api/v1/review/pending/{review_id}", json={"action": "approve", "corrected_value": "1990-01-01"})
    assert resp2.status_code == 400
    assert "Only PENDING reviews can be modified" in resp2.json()["detail"]
