import pytest
import uuid
from pathlib import Path
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from tests.conftest import TestingSessionLocal
from app.models.audit_log import AuditLogEntry
from app.core.security import create_access_token

client = TestClient(app)

def get_admin_token():
    return create_access_token(
        data={"sub": "aaaa0000-0000-0000-0000-000000000111", "role": "hospital_admin", "email": "admin@clinic.org"}
    )

@pytest.fixture
def policy_dir(tmp_path):
    return tmp_path

@pytest.fixture
def auth_headers():
    token = get_admin_token()
    return {"Authorization": f"Bearer {token}"}

def test_policy_chatbot_audit_logging(auth_headers, policy_dir, monkeypatch):
    import app.routers.policy_chatbot
    monkeypatch.setattr(app.routers.policy_chatbot, "DEFAULT_POLICY_DOCUMENTS_DIR", str(policy_dir))
    
    db = TestingSessionLocal()
    db.query(AuditLogEntry).delete()
    db.commit()
    db.close()

    # 1. Test policy_document_ingested
    with patch("app.routers.policy_chatbot.ingest_policy_documents", return_value=5):
        files = {"files": ("test_policy.md", b"# Policy\nBe good.", "text/markdown")}
        upload_res = client.post("/api/v1/policy-chat/upload", files=files, headers=auth_headers)
        assert upload_res.status_code == 201
        
    db = TestingSessionLocal()
    logs = db.query(AuditLogEntry).filter(AuditLogEntry.action_type == "policy_document_ingested").all()
    assert len(logs) == 1
    assert logs[0].target_entity == "policy_document:test_policy.md"
    assert logs[0].patient_id is None
    db.close()

    # 2. Test policy_rag_query
    mock_chunk = MagicMock()
    mock_chunk.chunk.source_document_id = "test_policy.md"
    mock_chunk.chunk.metadata_json = {"section_heading": "Rules"}
    
    with patch("app.routers.policy_chatbot.retrieve_relevant_policy_chunks", return_value=[mock_chunk]), \
         patch("app.routers.policy_chatbot.generate_policy_answer", return_value="You must be good."):
        
        chat_res = client.post("/api/v1/policy-chat", json={"question": "What are the rules?"}, headers=auth_headers)
        assert chat_res.status_code == 200
        
    db = TestingSessionLocal()
    logs = db.query(AuditLogEntry).filter(AuditLogEntry.action_type == "policy_rag_query").all()
    assert len(logs) == 1
    assert logs[0].target_entity == "policy_index"
    assert logs[0].patient_id is None
    db.close()

    # 3. Test policy_source_viewed
    source_res = client.get("/api/v1/policy-chat/source/test_policy.md", headers=auth_headers)
    assert source_res.status_code == 200

    db = TestingSessionLocal()
    logs = db.query(AuditLogEntry).filter(AuditLogEntry.action_type == "policy_source_viewed").all()
    assert len(logs) == 1
    assert logs[0].target_entity == "policy_document:test_policy.md"
    assert logs[0].patient_id is None
    db.close()
