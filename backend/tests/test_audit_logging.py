import pytest
import uuid
import json
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.patient import Patient
from app.models.document import Document
from app.models.pending_review import PendingReview, ReviewStatus
from app.models.user import User, UserRole
from app.core.security import get_current_user
from app.models.audit_log import AuditLogEntry
from tests.conftest import TestingSessionLocal
from app.services import audit_service
from tests.test_upload import make_valid_pdf_bytes, wait_for_document_processing
from app.services import audit_service
from tests.test_upload import make_valid_pdf_bytes, wait_for_document_processing


client = TestClient(app)

TEST_USER_ID = str(uuid.uuid4())

def override_get_current_user():
    u = User(id=uuid.UUID(TEST_USER_ID), email="audit_test@clinic.org", role=UserRole.DOCTOR)
    u.patient_access = ["test_rag_patient", "test_audit_patient"]
    return u

@pytest.fixture(autouse=True)
def setup_auth_override():
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

def test_audit_log_document_upload_and_extract():
    """Test that uploading a document triggers document_uploaded and document_extracted logs."""
    db = TestingSessionLocal()
    # Ensure audit log is empty before test
    db.query(AuditLogEntry).delete()
    db.commit()
    db.close()

    # Create dummy file to upload
    file_content = make_valid_pdf_bytes()
    
    import io
    # Upload via client
    response = client.post(
        "/api/v1/documents/upload",
        files=[("files", ("test_audit_upload.pdf", io.BytesIO(file_content), "application/pdf"))]
    )
    
    assert response.status_code == 201
    data = response.json()
    assert data["accepted_count"] == 1
    doc_id = data["accepted"][0]["document_id"]
    
    # Wait for document processing to finish (classification & extraction)
    wait_for_document_processing(client, doc_id)
    
    db = TestingSessionLocal()
    logs = db.query(AuditLogEntry).filter(AuditLogEntry.actor_user_id == uuid.UUID(TEST_USER_ID)).all()
    
    upload_logs = [log for log in logs if log.action_type == "document_uploaded"]
    extract_logs = [log for log in logs if log.action_type == "document_extracted"]
    
    assert len(upload_logs) == 1, "Expected exactly one document_uploaded log"
    assert upload_logs[0].target_entity == f"document:{doc_id}"
    
    assert len(extract_logs) == 1, "Expected exactly one document_extracted log"
    assert extract_logs[0].target_entity == f"document:{doc_id}"
    
    db.close()


def test_audit_log_review_action_and_canonical_write():
    """Test that approving a review item triggers review_action and canonical_record_write logs."""
    db = TestingSessionLocal()
    db.query(AuditLogEntry).delete()
    db.commit()

    doc_id = str(uuid.uuid4())
    doc = Document(document_id=doc_id, patient_id="test_audit_patient", filename="review_test.pdf", raw_uri="/test/uri", filetype="application/pdf", status="PENDING")
    db.add(doc)

    review_id = str(uuid.uuid4())
    review_item = PendingReview(
        id=review_id,
        document_id=doc_id,
        field_name="blood_pressure",
        extracted_value="120/80",
        confidence_score=0.4,
        status=ReviewStatus.PENDING
    )
    db.add(review_item)
    db.commit()
    db.close()

    # Action: Approve
    response = client.patch(
        f"/api/v1/review/pending/{review_id}",
        json={"action": "approve", "corrected_value": "120/82"}
    )
    assert response.status_code == 200

    db = TestingSessionLocal()
    logs = db.query(AuditLogEntry).filter(AuditLogEntry.actor_user_id == uuid.UUID(TEST_USER_ID)).all()
    
    review_logs = [log for log in logs if log.action_type == "review_approve"]
    canonical_logs = [log for log in logs if log.action_type == "canonical_record_write"]

    assert len(review_logs) == 1, "Expected exactly one review_approve log"
    assert review_logs[0].target_entity == f"pending_review:{review_id}"

    assert len(canonical_logs) >= 1, "Expected canonical_record_write log on approve"
    db.close()


@patch("app.config.settings.GEMINI_API_KEY", "dummy_key")
@patch("google.genai.Client")
def test_audit_log_rag_query(mock_genai_client):
    """Test that a RAG query (even without grounded answer) triggers rag_query log."""
    db = TestingSessionLocal()
    db.query(AuditLogEntry).delete()
    
    patient_id = "test_audit_patient"
    patient = Patient(patient_id=patient_id, mrn="MRN-AUDIT", name="Audit Test Patient")
    db.add(patient)
    db.commit()
    db.close()

    mock_client_instance = mock_genai_client.return_value
    mock_embed_response = MagicMock()
    mock_embed_response.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
    mock_client_instance.models.embed_content.return_value = mock_embed_response
    
    mock_generate_response = MagicMock()
    mock_generate_response.text = "I could not find any relevant information."
    mock_client_instance.models.generate_content.return_value = mock_generate_response

    response = client.post(
        f"/api/v1/patients/{patient_id}/ask",
        json={"question": "What is the diagnosis?"}
    )
    assert response.status_code == 200

    db = TestingSessionLocal()
    logs = db.query(AuditLogEntry).filter(AuditLogEntry.actor_user_id == uuid.UUID(TEST_USER_ID)).all()
    
    rag_logs = [log for log in logs if log.action_type == "rag_query"]
    
    assert len(rag_logs) == 1, "Expected exactly one rag_query log"
    assert rag_logs[0].target_entity == f"patient:{patient_id}"
    assert "Grounded answer found: False" in rag_logs[0].rationale
    
    db.close()
