import pytest
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.models.patient import Patient
from app.models.rag_chunk import PatientRAGChunk
from tests.conftest import TestingSessionLocal
from unittest.mock import patch, MagicMock
from app.core.security import get_current_user
from app.models.user import User, UserRole

client = TestClient(app)

def override_get_current_user():
    u = User(id=uuid.uuid4(), email="test@test.com", role=UserRole.DOCTOR)
    u.patient_access = [
        "test_rag_patient", "patient_citation_test", "patient_a", "patient_b", "patient_zero", "patient_no_key", "test_patient", "any_patient", "nonexistent_patient"
    ]
    return u

@pytest.fixture(autouse=True)
def setup_rag_auth():
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)

def test_ask_unauthorized():
    """Test that /ask returns 401 without a valid bearer token."""
    old_override = app.dependency_overrides.pop(get_current_user, None)
    try:
        response = client.post(
            "/api/v1/patients/test_patient/ask",
            json={"question": "What is the history?"}
        )
        assert response.status_code == 401
    finally:
        if old_override:
            app.dependency_overrides[get_current_user] = old_override


@patch("app.config.settings.GEMINI_API_KEY", "dummy_key")
@patch("google.genai.Client")
def test_ask_patient_question(mock_genai_client):
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    db = TestingSessionLocal()
    try:
        patient = Patient(patient_id="test_rag_patient", mrn="MRN-RAG", name="RAG Test Patient")
        db.add(patient)
        
        chunk = PatientRAGChunk(
            patient_id="test_rag_patient",
            source_document_id="doc1",
            content="Patient has a history of asthma.",
            embedding=[0.1, 0.2, 0.3], 
            metadata_json={"document_type": "Discharge Summary"}
        )
        db.add(chunk)
        db.commit()
    finally:
        db.close()
        
    mock_client_instance = mock_genai_client.return_value
    mock_embed_response = MagicMock()
    mock_embed_response.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
    mock_client_instance.models.embed_content.return_value = mock_embed_response
    
    mock_generate_response = MagicMock()
    mock_generate_response.text = "The patient has a history of asthma."
    mock_client_instance.models.generate_content.return_value = mock_generate_response
    
    response = client.post(
        "/api/v1/patients/test_rag_patient/ask",
        json={"question": "What is the patient's medical history?"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "The patient has a history of asthma."
    assert len(data["source_documents"]) > 0
    assert data["source_documents"][0]["document_id"] == "doc1"
    assert data["source_documents"][0]["snippet"] == "Patient has a history of asthma."
    assert data["source_documents"][0]["location"] == "Discharge Summary"
    
    pass


@patch("app.config.settings.GEMINI_API_KEY", "dummy_key")
@patch("google.genai.Client")
def test_rag_citation_object_structure(mock_genai_client):
    """
    Confirm that a chat response's citation object includes both a non-null document_id
    and a non-empty snippet string.
    """
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    db = TestingSessionLocal()
    try:
        patient = Patient(patient_id="patient_citation_test", mrn="MRN-CIT", name="Citation Test Patient")
        db.add(patient)
        
        chunk = PatientRAGChunk(
            patient_id="patient_citation_test",
            source_document_id="doc_synth_999",
            content="Synthetic patient was prescribed Amoxicillin 500mg daily.",
            embedding=[0.1, 0.2, 0.3], 
            metadata_json={"page_number": 1, "document_type": "Prescription"}
        )
        db.add(chunk)
        db.commit()
    finally:
        db.close()
        
    mock_client_instance = mock_genai_client.return_value
    mock_embed_response = MagicMock()
    mock_embed_response.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
    mock_client_instance.models.embed_content.return_value = mock_embed_response
    
    mock_generate_response = MagicMock()
    mock_generate_response.text = "The patient was prescribed Amoxicillin 500mg daily."
    mock_client_instance.models.generate_content.return_value = mock_generate_response
    
    response = client.post(
        "/api/v1/patients/patient_citation_test/ask",
        json={"question": "What medication was prescribed?"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "source_documents" in data
    assert len(data["source_documents"]) > 0
    
    citation = data["source_documents"][0]
    assert citation["document_id"] is not None
    assert isinstance(citation["document_id"], str)
    assert len(citation["document_id"]) > 0
    assert citation["document_id"] == "doc_synth_999"
    
    assert citation["snippet"] is not None
    assert isinstance(citation["snippet"], str)
    assert len(citation["snippet"]) > 0
    assert "Amoxicillin" in citation["snippet"]
    
    assert citation["location"] == "Page 1"
    
    pass



@patch("app.config.settings.GEMINI_API_KEY", "dummy_key")
@patch("google.genai.Client")
def test_ask_patient_isolation(mock_genai_client):
    """
    Patient isolation: seed chunks for two different patients, ask a question whose 
    answer only exists in patient B's chunks while querying patient A — assert the 
    fallback 'no grounded answer' message is returned, not an answer sourced from B.
    """
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    db = TestingSessionLocal()
    try:
        patient_a = Patient(patient_id="patient_a", mrn="MRN-A", name="Patient A")
        patient_b = Patient(patient_id="patient_b", mrn="MRN-B", name="Patient B")
        db.add_all([patient_a, patient_b])
        
        # Add chunk only to patient B
        chunk_b = PatientRAGChunk(
            patient_id="patient_b",
            source_document_id="doc_b",
            content="Patient B has diabetes.",
            embedding=[0.1, 0.2, 0.3],
        )
        db.add(chunk_b)
        db.commit()
    finally:
        db.close()
        
    mock_client_instance = mock_genai_client.return_value
    mock_embed_response = MagicMock()
    mock_embed_response.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
    mock_client_instance.models.embed_content.return_value = mock_embed_response
    
    response = client.post(
        "/api/v1/patients/patient_a/ask",
        json={"question": "Does the patient have diabetes?"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "could not find any relevant information" in data["answer"].lower()
    
    pass


@patch("app.config.settings.GEMINI_API_KEY", "dummy_key")
def test_ask_patient_404():
    """404 when patient_id doesn't exist."""
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    response = client.post(
        "/api/v1/patients/nonexistent_patient/ask",
        json={"question": "Hello?"}
    )
    
    assert response.status_code == 404
    
    pass


@patch("app.config.settings.GEMINI_API_KEY", "dummy_key")
@patch("google.genai.Client")
def test_ask_zero_chunks(mock_genai_client):
    """Fallback message when a patient has zero indexed chunks."""
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    db = TestingSessionLocal()
    try:
        patient = Patient(patient_id="patient_zero", mrn="MRN-Z", name="Zero Chunks")
        db.add(patient)
        db.commit()
    finally:
        db.close()
        
    mock_client_instance = mock_genai_client.return_value
    mock_embed_response = MagicMock()
    mock_embed_response.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
    mock_client_instance.models.embed_content.return_value = mock_embed_response
    
    response = client.post(
        "/api/v1/patients/patient_zero/ask",
        json={"question": "What is the history?"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "could not find any relevant information" in data["answer"].lower()
    
    pass


@patch("app.config.settings.GEMINI_API_KEY", "")
def test_ask_missing_api_key():
    """Missing GEMINI_API_KEY returns a 500 with a clear error, not a crash."""
    app.dependency_overrides[get_current_user] = override_get_current_user
    
    db = TestingSessionLocal()
    try:
        patient = Patient(patient_id="patient_no_key", mrn="MRN-NK", name="No Key")
        db.add(patient)
        db.commit()
    finally:
        db.close()
        
    response = client.post(
        "/api/v1/patients/patient_no_key/ask",
        json={"question": "What is the history?"}
    )
    
    assert response.status_code == 500
    data = response.json()
    assert "GEMINI_API_KEY is not set" in data["detail"]
    
    pass
