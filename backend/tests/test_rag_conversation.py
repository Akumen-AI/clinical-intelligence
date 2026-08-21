import pytest
from unittest.mock import patch, MagicMock
from app.models.rag_conversation import RAGConversation
from app.models.rag_chunk import PatientRAGChunk
from app.models.patient import Patient
from app.models.audit_log import AuditLogEntry
from app.core.security import create_access_token
from app.models.user import UserRole
import uuid
from tests.conftest import TestingSessionLocal

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def mock_gemini_client():
    with patch("google.genai.Client") as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def setup_rag_patient(db_session):
    patient_id = "rag-conv-patient-1"
    patient = Patient(patient_id=patient_id, patient_number="PT-RAG-1", mrn="MRN-RAG-1", name="RAG Test Patient")
    db_session.add(patient)
    
    # Add some chunks
    chunk1 = PatientRAGChunk(
        patient_id=patient_id,
        source_document_id="doc-1",
        content="Patient is taking Lisinopril for high blood pressure.",
        embedding=[0.1] * 768,
    )
    chunk2 = PatientRAGChunk(
        patient_id=patient_id,
        source_document_id="doc-2",
        content="Patient has a history of Type 2 Diabetes.",
        embedding=[0.2] * 768,
    )
    db_session.add_all([chunk1, chunk2])
    db_session.commit()
    return patient_id

from app.main import app
from app.core.security import get_current_user
from app.models.user import User, UserRole
from fastapi.testclient import TestClient

@pytest.fixture
def test_user_id():
    return str(uuid.uuid4())

@pytest.fixture
def auth_client(test_user_id):
    def override_get_current_user():
        # Ensure User gets a proper UUID object so it doesn't cause audit log crashes
        u = User(id=uuid.UUID(test_user_id), email="test@test.com", role=UserRole.DOCTOR)
        u.patient_access = ["rag-conv-patient-1", "rag-conv-patient-2"]
        return u
        
    app.dependency_overrides[get_current_user] = override_get_current_user
    c = TestClient(app)
    yield c
    app.dependency_overrides.pop(get_current_user, None)

def test_new_conversation_created(auth_client, setup_rag_patient, mock_gemini_client):
    """Test (d): starting a new conversation when no conversation_id is given."""
    # Mock LLM response
    mock_response = MagicMock()
    mock_response.text = "Lisinopril"
    mock_gemini_client.models.generate_content.return_value = mock_response
    
    # Mock embeddings
    with patch("app.services.rag_service.get_embedding", return_value=[0.1]*768):
        response = auth_client.post(
            f"/api/v1/patients/{setup_rag_patient}/ask",
            json={"question": "What medication is the patient taking?"}
        )
        if response.status_code != 200:
            print("ERROR RESPONSE:", response.json())
        assert response.status_code == 200
    data = response.json()
    assert "conversation_id" in data
    assert data["conversation_id"] is not None
    assert data["answer"] == "Lisinopril"

def test_followup_question_resolves(auth_client, db_session, setup_rag_patient, mock_gemini_client, test_user_id):
    """Test (a): a follow-up question resolves using prior turn context in ≥2 scenarios."""
    # Scenario 1: Resolving a pronoun
    conv = RAGConversation(
        patient_id=setup_rag_patient, 
        user_id=test_user_id, 
        turns=[
            {"role": "user", "content": "What medications?"},
            {"role": "assistant", "content": "Lisinopril"}
        ]
    )
    db_session.add(conv)
    db_session.commit()
    
    # Mock rewrite to prove it gets called
    mock_rewrite_response = MagicMock()
    mock_rewrite_response.text = "What is Lisinopril for?"
    
    mock_answer_response = MagicMock()
    mock_answer_response.text = "High blood pressure."
    
    # generate_content is called twice: once for rewrite, once for answer
    mock_gemini_client.models.generate_content.side_effect = [mock_rewrite_response, mock_answer_response]
    
    with patch("app.services.rag_service.get_embedding", return_value=[0.1]*768):
        response = auth_client.post(
            f"/api/v1/patients/{setup_rag_patient}/ask",
            json={"question": "What is it for?", "conversation_id": conv.id}
        )
        if response.status_code != 200:
            print("ERROR RESPONSE:", response.json())
        assert response.status_code == 200
    assert mock_gemini_client.models.generate_content.call_count == 2
    
    # Verify the history context was passed in the second call (the answer prompt)
    second_call_args = mock_gemini_client.models.generate_content.call_args_list[1]
    prompt_text = second_call_args[1]["contents"]
    assert "Conversation History" in prompt_text
    assert "What medications?" in prompt_text
    assert "Lisinopril" in prompt_text
    
    db_session.refresh(conv)
    assert len(conv.turns) == 4
    assert conv.turns[2]["content"] == "What is it for?"
    assert conv.turns[3]["content"] == "High blood pressure."

    # Scenario 2: Resolving a referential phrase like "the other one"
    conv2 = RAGConversation(
        patient_id=setup_rag_patient, 
        user_id=test_user_id, 
        turns=[
            {"role": "user", "content": "List their conditions."},
            {"role": "assistant", "content": "They have high blood pressure and diabetes."}
        ]
    )
    db_session.add(conv2)
    db_session.commit()
    
    mock_gemini_client.models.generate_content.reset_mock()
    mock_rewrite2 = MagicMock()
    mock_rewrite2.text = "Tell me more about diabetes."
    mock_ans2 = MagicMock()
    mock_ans2.text = "It is Type 2."
    mock_gemini_client.models.generate_content.side_effect = [mock_rewrite2, mock_ans2]
    
    with patch("app.services.rag_service.get_embedding", return_value=[0.2]*768):
        response2 = auth_client.post(
            f"/api/v1/patients/{setup_rag_patient}/ask",
            json={"question": "Tell me more about the second one.", "conversation_id": conv2.id}
        )
        if response2.status_code != 200:
            print("ERROR RESPONSE:", response2.json())
        assert response2.status_code == 200
    assert mock_gemini_client.models.generate_content.call_count == 2
    
def test_conversation_isolation_across_patients(auth_client, db_session, setup_rag_patient, test_user_id):
    """Test (b): conversation isolation across patients."""
    patient2_id = "rag-conv-patient-2"
    patient2 = Patient(patient_id=patient2_id, patient_number="PT-RAG-2", mrn="MRN-RAG-2", name="Another Patient")
    db_session.add(patient2)
    
    # Create conversation for patient 1
    conv = RAGConversation(patient_id=setup_rag_patient, user_id=str(test_user_id), turns=[])
    db_session.add(conv)
    db_session.commit()
    
    # Attempt to use patient 1's conversation ID for patient 2
    response = auth_client.post(
        f"/api/v1/patients/{patient2_id}/ask",
        json={"question": "hello?", "conversation_id": conv.id}
    )
    
    assert response.status_code == 403
    assert "Invalid conversation ID" in response.json()["detail"]

def test_conversation_isolation_across_users(auth_client, db_session, setup_rag_patient, test_user_id):
    """Test (c): conversation isolation across users."""
    # Create conversation belonging to someone else
    other_user_id = str(uuid.uuid4())
    conv = RAGConversation(patient_id=setup_rag_patient, user_id=other_user_id, turns=[])
    db_session.add(conv)
    db_session.commit()
    
    # Attempt to use it with our token (which belongs to test-user-id)
    response = auth_client.post(
        f"/api/v1/patients/{setup_rag_patient}/ask",
        json={"question": "hello?", "conversation_id": conv.id}
    )
    
    assert response.status_code == 403
    assert "Invalid conversation ID" in response.json()["detail"]

def test_audit_logs_written(auth_client, db_session, setup_rag_patient, mock_gemini_client, test_user_id):
    """Test (e): audit log entries still get written per turn."""
    mock_response = MagicMock()
    mock_response.text = "Lisinopril"
    mock_gemini_client.models.generate_content.return_value = mock_response
    
    initial_log_count = db_session.query(AuditLogEntry).count()
    
    with patch("app.services.rag_service.get_embedding", return_value=[0.1]*768):
        auth_client.post(
            f"/api/v1/patients/{setup_rag_patient}/ask",
            json={"question": "What is the medication?"}
        )
        
    final_log_count = db_session.query(AuditLogEntry).count()
    assert final_log_count > initial_log_count
    
    latest_log = db_session.query(AuditLogEntry).order_by(AuditLogEntry.timestamp.desc()).first()
    assert latest_log.action_type == "rag_query"
    assert f"patient:{setup_rag_patient}" in latest_log.target_entity
