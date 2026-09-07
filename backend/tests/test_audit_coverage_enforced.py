import pytest
import uuid
import io
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.models.patient import Patient
from app.models.document import Document
from app.models.pending_review import PendingReview, ReviewStatus
from app.models.user import User, UserRole
from app.core.security import get_current_user
from app.models.audit_log import AuditLogEntry
from tests.conftest import TestingSessionLocal
from tests.test_upload import make_valid_pdf_bytes, wait_for_document_processing

client = TestClient(app)
TEST_USER_ID = str(uuid.uuid4())

def override_get_current_user():
    u = User(id=uuid.UUID(TEST_USER_ID), email="audit_enforcer@clinic.org", role=UserRole.HOSPITAL_ADMIN)
    u.patient_access = ["e2e_patient", "dec_patient", "dec_patient_review"]
    return u

@pytest.fixture(autouse=True)
def setup_auth_override():
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

@pytest.fixture
def clear_audit_log():
    db = TestingSessionLocal()
    db.query(AuditLogEntry).delete()
    db.commit()
    db.close()


def test_declarative_upload(clear_audit_log):
    file_content = make_valid_pdf_bytes()
    response = client.post(
        "/api/v1/documents/upload",
        files=[("files", ("test_audit.pdf", io.BytesIO(file_content), "application/pdf"))]
    )
    assert response.status_code == 201
    doc_id = response.json()["accepted"][0]["document_id"]
    wait_for_document_processing(client, doc_id)

    db = TestingSessionLocal()
    logs = db.query(AuditLogEntry).all()
    action_types = {log.action_type for log in logs}
    assert "document_uploaded" in action_types
    assert "document_extracted" in action_types
    db.close()


def test_declarative_link_patient(clear_audit_log):
    db = TestingSessionLocal()
    patient = Patient(patient_id="dec_patient", mrn="MRN-DEC", name="Dec Patient")
    doc = Document(document_id="dec_doc", patient_id=None, filename="dec.pdf", raw_uri="/test/uri", filetype="application/pdf", status="PROCESSED")
    db.merge(patient)
    db.add(doc)
    db.commit()
    db.close()

    response = client.post(
        "/api/v1/documents/dec_doc/link-patient",
        json={"patient_id": "dec_patient"}
    )
    assert response.status_code == 200

    db = TestingSessionLocal()
    logs = db.query(AuditLogEntry).all()
    action_types = {log.action_type for log in logs}
    assert "document_linked_to_patient" in action_types
    db.close()


def test_declarative_review_patch(clear_audit_log):
    db = TestingSessionLocal()
    patient = Patient(patient_id="dec_patient_review", mrn="MRN-DEC-REV", name="Dec Patient")
    doc = Document(document_id="dec_doc_review", patient_id="dec_patient_review", filename="dec.pdf", raw_uri="/test/uri", filetype="application/pdf", status="PROCESSED")
    review = PendingReview(id="dec_rev", document_id="dec_doc_review", field_name="blood_pressure", extracted_value="120/80", confidence_score=0.4, status=ReviewStatus.PENDING)
    db.merge(patient)
    db.add(doc)
    db.add(review)
    db.commit()
    db.close()

    response = client.patch(
        "/api/v1/review/pending/dec_rev",
        json={"action": "approve", "corrected_value": "120/82"}
    )
    assert response.status_code == 200

    db = TestingSessionLocal()
    logs = db.query(AuditLogEntry).all()
    action_types = {log.action_type for log in logs}
    assert "review_approve" in action_types
    assert "canonical_record_write" in action_types
    db.close()


def test_declarative_dashboards(clear_audit_log):
    db = TestingSessionLocal()
    patient = Patient(patient_id="dec_patient", mrn="MRN-DEC", name="Dec Patient")
    db.merge(patient)
    db.commit()
    db.close()

    res1 = client.get("/api/v1/dashboards/patient/dec_patient")
    assert res1.status_code == 200
    res2 = client.get("/api/v1/dashboards/department", params={"department": "Cardiology"})
    assert res2.status_code == 200
    res3 = client.get("/api/v1/dashboards/hospital")
    assert res3.status_code == 200

    db = TestingSessionLocal()
    logs = db.query(AuditLogEntry).all()
    action_types = {log.action_type for log in logs}
    assert "patient_dashboard_viewed" in action_types
    assert "department_dashboard_viewed" in action_types
    assert "hospital_dashboard_viewed" in action_types
    db.close()


@pytest.mark.asyncio
async def test_declarative_correction_export(async_client, clear_audit_log, db_session):
    from app.models.correction_log import CorrectionLog
    from datetime import datetime, timezone
    
    log = CorrectionLog(
        extracted_field_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        action="edit",
        before_value="foo",
        field_name="test",
        reviewer_id=uuid.uuid4(),
        reviewed_at=datetime.now(timezone.utc)
    )
    db_session.add(log)
    await db_session.commit()

    response = await async_client.post("/api/v1/correction-logs/export/retraining")
    assert response.status_code == 200

    from sqlalchemy import select
    result = await db_session.execute(select(AuditLogEntry))
    logs = result.scalars().all()
    action_types = {log.action_type for log in logs}
    assert "correction_log_export" in action_types


def test_declarative_policy(clear_audit_log, tmp_path, monkeypatch):
    import app.routers.policy_chatbot
    monkeypatch.setattr(app.routers.policy_chatbot, "DEFAULT_POLICY_DOCUMENTS_DIR", str(tmp_path))

    with patch("app.routers.policy_chatbot.ingest_policy_documents", return_value=1):
        res1 = client.post(
            "/api/v1/policy-chat/upload",
            files={"files": ("test_pol.md", b"# Policy\nTest", "text/markdown")}
        )
        assert res1.status_code == 201

    mock_chunk = MagicMock()
    mock_chunk.chunk.source_document_id = "test_pol.md"
    with patch("app.routers.policy_chatbot.retrieve_relevant_policy_chunks", return_value=[mock_chunk]), \
         patch("app.routers.policy_chatbot.generate_policy_answer", return_value="Test answer"):
        res2 = client.post("/api/v1/policy-chat", json={"question": "Test?"})
        assert res2.status_code == 200

    res3 = client.get("/api/v1/policy-chat/source/test_pol.md")
    assert res3.status_code == 200

    db = TestingSessionLocal()
    logs = db.query(AuditLogEntry).all()
    action_types = {log.action_type for log in logs}
    assert "policy_document_ingested" in action_types
    assert "policy_rag_query" in action_types
    assert "policy_source_viewed" in action_types
    db.close()


@patch("app.config.settings.GEMINI_API_KEY", "dummy_key")
@patch("google.genai.Client")
def test_declarative_rag(mock_genai_client, clear_audit_log):
    db = TestingSessionLocal()
    patient = Patient(patient_id="dec_patient", mrn="MRN-DEC", name="Dec Patient")
    db.merge(patient)
    db.commit()
    db.close()

    class MockEmbedding:
        def __init__(self):
            self.values = [0.1] * 768
            
    mock_client_instance = mock_genai_client.return_value
    mock_client_instance.models.embed_content.return_value.embeddings = [MockEmbedding()]
    mock_client_instance.models.generate_content.return_value.text = "Answer"

    res = client.post("/api/v1/patients/dec_patient/ask", json={"question": "Test?"})
    assert res.status_code == 200

    db = TestingSessionLocal()
    logs = db.query(AuditLogEntry).all()
    action_types = {log.action_type for log in logs}
    assert "rag_query" in action_types
    db.close()


@patch("app.config.settings.GEMINI_API_KEY", "dummy_key")
@patch("google.genai.Client")
def test_e2e_patient_audit_reconstruction(mock_genai_client, clear_audit_log):
    class MockEmbedding:
        def __init__(self):
            self.values = [0.1] * 768

    mock_client_instance = mock_genai_client.return_value
    mock_client_instance.models.embed_content.return_value.embeddings = [MockEmbedding()]
    mock_client_instance.models.generate_content.return_value.text = "Answer"

    db = TestingSessionLocal()
    # E2E test needs a fresh patient to ensure isolated events
    patient = Patient(patient_id="e2e_patient", mrn="MRN-E2E", name="E2E Patient")
    db.merge(patient)
    db.commit()
    db.close()

    # 1. Upload a document
    file_content = make_valid_pdf_bytes()
    upload_res = client.post(
        "/api/v1/documents/upload",
        files=[("files", ("e2e_test.pdf", io.BytesIO(file_content), "application/pdf"))]
    )
    assert upload_res.status_code == 201
    doc_id = upload_res.json()["accepted"][0]["document_id"]
    wait_for_document_processing(client, doc_id)

    # 2. Link it to a patient
    link_res = client.post(
        f"/api/v1/documents/{doc_id}/link-patient",
        json={"patient_id": "e2e_patient"}
    )
    assert link_res.status_code == 200

    # Create a pending review for it so we can approve it
    db = TestingSessionLocal()
    rev_id = str(uuid.uuid4())
    review = PendingReview(id=rev_id, document_id=doc_id, field_name="blood_pressure", extracted_value="120/80", confidence_score=0.4, status=ReviewStatus.PENDING)
    db.add(review)
    db.commit()
    db.close()

    # 3. Approve review item
    appr_res = client.patch(
        f"/api/v1/review/pending/{rev_id}",
        json={"action": "approve", "corrected_value": "120/82"}
    )
    assert appr_res.status_code == 200

    # 4. View patient dashboard
    dash_res = client.get("/api/v1/dashboards/patient/e2e_patient")
    assert dash_res.status_code == 200

    # 5. Ask RAG question
    rag_res = client.post("/api/v1/patients/e2e_patient/ask", json={"question": "Test?"})
    assert rag_res.status_code == 200

    # Now verify the reconstruction
    from app.core.security import create_access_token, get_current_user
    from fastapi.testclient import TestClient
    from app.main import app

    app.dependency_overrides.pop(get_current_user, None)
    try:
        comp_token = create_access_token({"sub": str(uuid.uuid4()), "role": "compliance", "email": "comp@clinic.org"})
        comp_client = TestClient(app)
        comp_client.headers.update({"Authorization": f"Bearer {comp_token}"})
        
        audit_res = comp_client.get("/api/v1/audit-log/patient/e2e_patient")
        if audit_res.status_code != 200:
            print("AUDIT RES ERROR:", audit_res.json())
        assert audit_res.status_code == 200
        entries = audit_res.json()
    finally:
        app.dependency_overrides[get_current_user] = override_get_current_user

    # Actions we expect on the patient:
    expected_actions = {
        "document_uploaded",
        "document_extracted",
        "document_linked_to_patient",
        "review_approve",
        "canonical_record_write",
        "patient_dashboard_viewed",
        "rag_query"
    }

    actual_actions = {entry["action_type"] for entry in entries}

    missing = expected_actions - actual_actions
    assert not missing, f"Missing expected audit actions for patient: {missing}"

    # Verify they are ordered descending (newest first)
    for i in range(len(entries) - 1):
        assert entries[i]["timestamp"] >= entries[i+1]["timestamp"]
