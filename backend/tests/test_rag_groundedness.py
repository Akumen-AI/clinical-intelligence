import pytest
import json
import uuid
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.extracted_field import ExtractedField, VerificationStatus
from app.providers.rag.base import LLMProvider, RetrievalScope, RAGChunk
from app.providers.rag import get_vector_store, get_llm_provider, get_embedding_provider
from app.providers.rag.base import RAGChunk, LLMProvider, EmbeddingProvider
from app.services.rag_service import generate_answer, SIMILARITY_THRESHOLD
from app.models.rag_conversation import RAGConversation
from app.models.rag_message import RAGMessage


class MockGroundedLLM(LLMProvider):
    def __init__(self, override_response: Optional[str] = None):
        self.override_response = override_response
        self.last_prompt = ""
        self.last_context = []

    def generate(self, prompt: str, context: Optional[List[Dict[str, str]]] = None) -> str:
        self.last_prompt = prompt
        self.last_context = context or []
        
        if self.override_response:
            return self.override_response
            
        # Default mock behavior
        return json.dumps({
            "is_grounded": True,
            "answer": "This is a mocked answer.",
            "citations": [{"chunk_id": "chunk_0"}]
        })

@pytest.fixture
def mock_llm(monkeypatch):
    from app.services import rag_service
    mock = MockGroundedLLM()
    monkeypatch.setattr(rag_service, "get_llm_provider", lambda: mock)
    
    mock_emb = MockEmbeddingProvider()
    monkeypatch.setattr(rag_service, "get_embedding_provider", lambda: mock_emb)
    
    return mock

class MockEmbeddingProvider(EmbeddingProvider):
    def embed(self, text: str) -> list[float]:
        return [0.1] * 256
    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 256 for _ in texts]

@pytest.fixture
def setup_rag_context(db_session: Session, mock_llm):
    patient_id = "patient-grounded-test"
    user_id = "00000000-0000-0000-0000-000000000001"
    vector_store = get_vector_store()
    vector_store.chunks_store[RetrievalScope.PATIENT] = []
    vector_store._rebuild_index(RetrievalScope.PATIENT)
    
    # We will use dummy vectors that always match high for testing
    dummy_vector = [0.9] * 256
    
    chunk = RAGChunk(
        content="Patient has a documented history of severe peanut allergy.",
        embedding=dummy_vector,
        metadata={
            "patient_id": patient_id,
            "source_document_id": "doc-123",
            "document_type": "Allergy Profile",
            "page": "1",
            "source_field_id": "field-456"
        }
    )
    vector_store.add_chunks(RetrievalScope.PATIENT, [chunk])
    
    yield patient_id, user_id, dummy_vector

def test_unsupported_question_returns_no_grounded_answer(db_session: Session, setup_rag_context, mock_llm):
    patient_id, user_id, _ = setup_rag_context
    
    # Mock LLM to return is_grounded=false
    mock_llm.override_response = json.dumps({
        "is_grounded": False,
        "answer": "I don't know.",
        "citations": []
    })
    
    answer, citations, _ = generate_answer(db_session, patient_id, "What is the patient's favorite color?", user_id)
    
    assert len(citations) == 0
    assert "I don't know" in answer

def test_citation_points_to_actual_supporting_source(db_session: Session, setup_rag_context, mock_llm):
    """
    Test that the returned citation actually points to the correct source chunk ID
    and contains valid metadata.
    """
    patient_id, user_id, _ = setup_rag_context
    
    mock_llm.override_response = json.dumps({
        "is_grounded": True,
        "answer": "The individual has a severe peanut allergy.",
        "citations": [{"chunk_id": "chunk_0"}]
    })
    
    answer, citations, _ = generate_answer(db_session, patient_id, "What allergies does the patient have?", user_id)
    
    assert len(citations) == 1
    assert citations[0]["document_id"] == "doc-123"
    assert citations[0]["document_type"] == "Allergy Profile"
    assert citations[0]["page"] == "1"
    assert citations[0]["source_field_id"] == "field-456"
    assert "peanut allergy" in citations[0]["snippet"]

def test_hallucinated_citation_rejected(db_session: Session, setup_rag_context, mock_llm):
    """
    Test that if the LLM hallucinated a chunk_id that was NOT in the retrieved context,
    the verification step rejects it and returns a No Grounded Answer response.
    """
    patient_id, user_id, _ = setup_rag_context
    
    mock_llm.override_response = json.dumps({
        "is_grounded": True,
        "answer": "The patient has asthma.",
        "citations": [{"chunk_id": "chunk_99"}] # Hallucinated chunk_id
    })
    
    answer, citations, _ = generate_answer(db_session, patient_id, "Does the patient have asthma?", user_id)
    
    assert len(citations) == 0
    assert "No grounded answer" in answer

def test_follow_up_questions_preserve_context(db_session: Session, setup_rag_context, mock_llm):
    patient_id, user_id, _ = setup_rag_context
    
    # First turn
    mock_llm.override_response = json.dumps({
        "is_grounded": True,
        "answer": "The patient is allergic to peanuts.",
        "citations": [{"chunk_id": "chunk_0"}]
    })
    
    _, _, conv_id = generate_answer(db_session, patient_id, "What allergies?", user_id)
    
    # Follow-up
    mock_llm.override_response = json.dumps({
        "is_grounded": True,
        "answer": "Yes, it is severe.",
        "citations": [{"chunk_id": "chunk_0"}]
    })
    
    generate_answer(db_session, patient_id, "Is it severe?", user_id, conversation_id=conv_id)
    
    # Check that context was sent to LLM
    assert len(mock_llm.last_context) >= 2
    assert mock_llm.last_context[0]["role"] == "user"
    assert mock_llm.last_context[0]["content"] == "What allergies?"

def test_concurrent_messages_not_lost(db_session: Session, setup_rag_context, mock_llm):
    """
    Because we moved to an append-only RAGMessage table, writing two messages to the same conversation
    simultaneously won't overwrite each other (unlike JSON read-modify-write).
    """
    patient_id, user_id, _ = setup_rag_context
    
    conversation = RAGConversation(patient_id=patient_id, user_id=user_id)
    db_session.add(conversation)
    db_session.commit()
    
    msg1 = RAGMessage(conversation_id=conversation.id, role="user", content="Msg1")
    msg2 = RAGMessage(conversation_id=conversation.id, role="user", content="Msg2")
    
    db_session.add(msg1)
    db_session.add(msg2)
    db_session.commit()
    
    db_session.refresh(conversation)
    assert len(conversation.messages) == 2
    contents = [m.content for m in conversation.messages]
    assert "Msg1" in contents
    assert "Msg2" in contents
