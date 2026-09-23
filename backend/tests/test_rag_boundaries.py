import pytest
import uuid
from app.providers.rag import get_vector_store, RetrievalScope, RAGChunk

def test_rag_scope_isolation():
    """
    Test that chunks added to the PATIENT scope cannot be retrieved from the POLICY scope,
    and vice versa, even if the embeddings are identical.
    """
    vector_store = get_vector_store()
    
    # Clean state
    vector_store.chunks_store[RetrievalScope.PATIENT] = []
    vector_store.chunks_store[RetrievalScope.POLICY] = []
    vector_store._rebuild_index(RetrievalScope.PATIENT)
    vector_store._rebuild_index(RetrievalScope.POLICY)
    
    # We will use a dummy 256-dimensional vector for both scopes
    dummy_vector = [0.1] * 256
    
    # 1. Add chunk to PATIENT scope
    patient_chunk = RAGChunk(
        content="Patient has diabetes.",
        embedding=dummy_vector,
        metadata={"patient_id": "test_patient_1"}
    )
    vector_store.add_chunks(RetrievalScope.PATIENT, [patient_chunk])
    
    # 2. Add chunk to POLICY scope
    policy_chunk = RAGChunk(
        content="Hospital policy for diabetes.",
        embedding=dummy_vector,
        metadata={"section": "Endocrinology"}
    )
    vector_store.add_chunks(RetrievalScope.POLICY, [policy_chunk])
    
    # 3. Search PATIENT scope (should return ONLY patient chunk)
    patient_results = vector_store.search(
        scope=RetrievalScope.PATIENT,
        query_vector=dummy_vector,
        top_k=5,
        filters={"patient_id": "test_patient_1"}
    )
    
    assert len(patient_results) == 1
    assert patient_results[0].content == "Patient has diabetes."
    
    # 4. Search POLICY scope (should return ONLY policy chunk)
    policy_results = vector_store.search(
        scope=RetrievalScope.POLICY,
        query_vector=dummy_vector,
        top_k=5,
        filters=None
    )
    
    assert len(policy_results) == 1
    assert policy_results[0].content == "Hospital policy for diabetes."

def test_patient_filter_isolation():
    """
    Test that within the PATIENT scope, filtering prevents retrieving 
    data belonging to a different patient.
    """
    vector_store = get_vector_store()
    
    # Clean state
    vector_store.chunks_store[RetrievalScope.PATIENT] = []
    vector_store._rebuild_index(RetrievalScope.PATIENT)
    
    dummy_vector = [0.1] * 256
    
    patient_a_chunk = RAGChunk(
        content="Patient A data.",
        embedding=dummy_vector,
        metadata={"patient_id": "patient_A"}
    )
    
    patient_b_chunk = RAGChunk(
        content="Patient B data.",
        embedding=dummy_vector,
        metadata={"patient_id": "patient_B"}
    )
    
    vector_store.add_chunks(RetrievalScope.PATIENT, [patient_a_chunk, patient_b_chunk])
    
    # Search for Patient A
    results_a = vector_store.search(
        scope=RetrievalScope.PATIENT,
        query_vector=dummy_vector,
        top_k=5,
        filters={"patient_id": "patient_A"}
    )
    
    assert len(results_a) == 1
    assert results_a[0].metadata["patient_id"] == "patient_A"
    
    # Search for Patient B
    results_b = vector_store.search(
        scope=RetrievalScope.PATIENT,
        query_vector=dummy_vector,
        top_k=5,
        filters={"patient_id": "patient_B"}
    )
    
    assert len(results_b) == 1
    assert results_b[0].metadata["patient_id"] == "patient_B"

