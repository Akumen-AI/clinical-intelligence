import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.patient import Patient
from app.models.rag_chunk import PatientRAGChunk
from tests.conftest import TestingSessionLocal
from unittest.mock import patch, MagicMock

client = TestClient(app)

@patch("google.genai.Client")
def test_ask_patient_question(mock_genai_client):
    db = TestingSessionLocal()
    try:
        # Setup: Create a patient
        patient = Patient(
            patient_id="test_rag_patient",
            mrn="MRN-RAG",
            name="RAG Test Patient"
        )
        db.add(patient)
        
        # Setup: Add a RAG chunk
        chunk = PatientRAGChunk(
            patient_id="test_rag_patient",
            source_document_id="doc1",
            content="Patient has a history of asthma.",
            embedding=[0.1, 0.2, 0.3], # Fake embedding
            metadata_json={"document_type": "Discharge Summary"}
        )
        db.add(chunk)
        db.commit()
    finally:
        db.close()
        
    # Mock embedding generation
    mock_client_instance = mock_genai_client.return_value
    mock_embed_response = MagicMock()
    mock_embed_response.embeddings = [MagicMock(values=[0.1, 0.2, 0.3])]
    mock_client_instance.models.embed_content.return_value = mock_embed_response
    
    # Mock content generation
    mock_generate_response = MagicMock()
    mock_generate_response.text = "The patient has a history of asthma."
    mock_client_instance.models.generate_content.return_value = mock_generate_response
    
    # Test the ask endpoint
    response = client.post(
        "/api/v1/patients/test_rag_patient/ask",
        json={"question": "What is the patient's medical history?"}
    )
    
    if response.status_code != 200:
        print(f"Error Response: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "The patient has a history of asthma."
    assert "doc1" in data["source_documents"]
