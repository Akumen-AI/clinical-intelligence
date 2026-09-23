import pytest
from sqlalchemy import inspect, text

from app.models.policy_rag_chunk import PolicyRAGChunk
from app.services import policy_ingestion_service, policy_rag_service
from tests.conftest import TestingSessionLocal, engine as test_engine


@pytest.fixture
def policy_runtime(monkeypatch, tmp_path):
    """Point the real policy ingestion and retrieval services at test-only state."""
    import app.routers.policy_chatbot as policy_chatbot_router

    # The checked-in local test database can predate the audit model's nullable
    # patient_id column. Keep these tests runnable against that database while
    # still exercising the real upload, audit, ingestion, and retrieval paths.
    with test_engine.begin() as connection:
        pass

    monkeypatch.setattr(policy_chatbot_router, "DEFAULT_POLICY_DOCUMENTS_DIR", str(tmp_path))
    monkeypatch.setattr(policy_ingestion_service, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(policy_ingestion_service, "engine", test_engine)
    monkeypatch.setattr(policy_rag_service, "SessionLocal", TestingSessionLocal)
    monkeypatch.setenv("POLICY_LLM_ENABLED", "0")
    return tmp_path


def _upload(client, filename: str, content: str):
    response = client.post(
        "/api/v1/policy-chat/upload",
        files={"files": (filename, content.encode("utf-8"), "text/markdown")},
    )
    assert response.status_code == 201, response.text
    return response


def test_upload_reindexes_and_chat_retrieves_new_document(client, policy_runtime):
    _upload(
        client,
        "new_policy.md",
        "## Section 1\nEmergency leave requests must be submitted within five business days.",
    )

    response = client.post(
        "/api/v1/policy-chat",
        json={"question": "How soon must emergency leave requests be submitted?"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert "five business days" in payload["answer"]
    assert any(citation["document_id"] == "new_policy.md" for citation in payload["citations"])


def test_same_filename_replaces_existing_indexed_content(client, policy_runtime):
    _upload(client, "retention.md", "## Section 1\nOld retention period is thirty days.")
    _upload(client, "retention.md", "## Section 1\nNew retention period is ninety days.")

    db = TestingSessionLocal()
    try:
        chunks = db.query(PolicyRAGChunk).filter(
            PolicyRAGChunk.source_document_id == "retention.md"
        ).all()
        contents = [chunk.content for chunk in chunks]
    finally:
        db.close()

    assert len(contents) == 1
    assert "Old retention period" not in contents[0]
    assert "New retention period is ninety days" in contents[0]

    matches = policy_rag_service.retrieve_relevant_policy_chunks(
        "What is the new retention period?"
    )
    assert any(
        match.chunk.source_document_id == "retention.md"
        and "ninety days" in match.chunk.content
        for match in matches
    )
    assert all("Old retention period" not in match.chunk.content for match in matches)


def test_retrieval_sees_upload_without_restart(client, policy_runtime):
    before_upload = policy_rag_service.retrieve_relevant_policy_chunks(
        "What is the confidential archive access code?"
    )
    assert before_upload == []

    _upload(
        client,
        "confidential.md",
        "## Section 1\nThe confidential archive access code is ORCHID-742.",
    )

    after_upload = policy_rag_service.retrieve_relevant_policy_chunks(
        "What is the confidential archive access code?"
    )
    assert any(
        match.chunk.source_document_id == "confidential.md"
        and "ORCHID-742" in match.chunk.content
        for match in after_upload
    )
