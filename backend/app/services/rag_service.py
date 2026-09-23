import json
import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.extracted_field import ExtractedField, VerificationStatus
from app.providers.rag import get_llm_provider, get_embedding_provider, get_vector_store, RetrievalScope, RAGChunk

logger = logging.getLogger("app.services.rag_service")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Split text into overlapping chunks based on characters."""
    if not text:
        return []
    chunks = []
    start = 0
    text_len = len(text)
    while start < text_len:
        end = min(start + chunk_size, text_len)
        if end < text_len:
            newline_pos = text.rfind('\n', max(start, end - 50), end)
            if newline_pos != -1:
                end = newline_pos + 1
            else:
                space_pos = text.rfind(' ', max(start, end - 20), end)
                if space_pos != -1:
                    end = space_pos + 1
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        next_start = end - overlap
        if next_start <= start:
            break
        start = next_start
    return chunks

def index_document(db: Session, document: Document, ocr_text: str):
    """
    Index a document and its verified extracted fields into the patient RAG index.
    Unverified fields are strictly excluded.
    """
    if not document.patient_id:
        return
        
    logger.info(f"[RAG] Indexing document {document.document_id} for patient {document.patient_id}")
    
    vector_store = get_vector_store()
    embedder = get_embedding_provider()
    
    # 1. Clean up existing chunks for this document
    vector_store.delete_chunks(RetrievalScope.PATIENT, filters={"source_document_id": document.document_id})
    
    chunks = []
    
    # 2. Index verified extracted fields (structured clinical facts)
    verified_fields = db.query(ExtractedField).filter(
        ExtractedField.document_id == document.document_id,
        ExtractedField.verification_status.in_(["HUMAN_VERIFIED", "AUTO_PASSED"])
    ).all()
    
    for field in verified_fields:
        text_content = f"{field.field_name}: {field.verified_value or field.raw_value}"
        embedding = embedder.embed(text_content)
        if embedding:
            chunks.append(RAGChunk(
                content=text_content,
                embedding=embedding,
                metadata={
                    "patient_id": document.patient_id,
                    "source_document_id": document.document_id,
                    "source_field_id": field.field_id,
                    "verification_state": field.verification_status,
                    "document_type": getattr(document, "document_type", "Unknown")
                }
            ))

    # 3. Only index the full OCR text if it's verified/safe, but for now we index the text chunks 
    # tagging them as 'ocr_text' so they can be distinguished from verified facts.
    text_chunks = chunk_text(ocr_text)
    for i, chunk_text_content in enumerate(text_chunks):
        embedding = embedder.embed(chunk_text_content)
        if embedding:
            chunks.append(RAGChunk(
                content=chunk_text_content,
                embedding=embedding,
                metadata={
                    "patient_id": document.patient_id,
                    "source_document_id": document.document_id,
                    "chunk_index": i,
                    "document_type": getattr(document, "document_type", "Unknown"),
                    "type": "ocr_text"
                }
            ))
            
    vector_store.add_chunks(RetrievalScope.PATIENT, chunks)
    logger.info(f"[RAG] Successfully indexed {len(chunks)} chunks for document {document.document_id}")


def retrieve_relevant_chunks(db: Session, patient_id: str, query: str, top_k: int = 5) -> List[Tuple[RAGChunk, float]]:
    embedder = get_embedding_provider()
    vector_store = get_vector_store()
    
    query_embedding = embedder.embed(query)
    if not query_embedding:
        return []
        
    # Strict Boundary: Hardcode RetrievalScope.PATIENT and filter by patient_id
    chunks = vector_store.search(
        scope=RetrievalScope.PATIENT,
        query_vector=query_embedding,
        top_k=top_k,
        filters={"patient_id": patient_id}
    )
    
    return [(chunk, chunk.metadata.get("_score", 0.0)) for chunk in chunks]


def generate_answer(db: Session, patient_id: str, question: str, user_id: str, conversation_id: str = None) -> Tuple[str, List[Dict[str, Any]], str]:
    from app.models.rag_conversation import RAGConversation
    
    llm = get_llm_provider()
    
    conversation = None
    if conversation_id:
        conversation = db.query(RAGConversation).filter(RAGConversation.id == conversation_id).first()
        if not conversation or conversation.patient_id != patient_id or conversation.user_id != str(user_id):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Invalid conversation ID for this patient and user.")
    else:
        conversation = RAGConversation(patient_id=patient_id, user_id=str(user_id), turns=[])
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    history_turns = conversation.turns[-10:] if conversation.turns else []
    
    search_query = question
    if history_turns:
        rewrite_prompt = "Given the following conversation history and the latest user question, rewrite the question to be a standalone question. Do not answer the question, just rewrite it. If it is already standalone, return it as is."
        try:
            rewritten = llm.generate(rewrite_prompt, context=history_turns)
            if rewritten:
                search_query = rewritten.strip()
        except Exception as e:
            logger.warning(f"[RAG] Failed to rewrite question for context: {e}")

    top_chunks = retrieve_relevant_chunks(db, patient_id, search_query, top_k=5)
    
    if not top_chunks:
        answer_text = "I could not find any relevant information in the patient's documents to answer your question."
        conversation.turns = conversation.turns + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer_text}
        ]
        db.commit()
        return answer_text, [], conversation.id
        
    context_parts = []
    citations = []
    seen = set()
    
    for i, (chunk, score) in enumerate(top_chunks):
        doc_type = chunk.metadata.get("document_type", "Unknown") if chunk.metadata else "Unknown"
        doc_id = chunk.metadata.get("source_document_id", "Unknown")
        context_parts.append(f"--- Document {doc_id} ({doc_type}) ---\n{chunk.content}")
        
        location = None
        if chunk.metadata:
            if "source_field_id" in chunk.metadata:
                location = "Structured Field"
            elif "section" in chunk.metadata and chunk.metadata["section"]:
                location = str(chunk.metadata["section"])
            elif "page_number" in chunk.metadata and chunk.metadata["page_number"]:
                location = f"Page {chunk.metadata['page_number']}"
            elif "page" in chunk.metadata and chunk.metadata["page"]:
                location = f"Page {chunk.metadata['page']}"
            elif "chunk_index" in chunk.metadata:
                location = f"Chunk {chunk.metadata['chunk_index']}"
            elif doc_type != "Unknown":
                location = doc_type

        chunk_key = (doc_id, chunk.content)
        if chunk_key not in seen:
            seen.add(chunk_key)
            citations.append({
                "document_id": doc_id,
                "snippet": chunk.content,
                "location": location,
            })
        
    context_str = "\n\n".join(context_parts)
    
    prompt = f"""You are a clinical AI assistant answering questions about a specific patient's medical record.
You will be provided with a set of retrieved text snippets from the patient's documents.
Answer the user's question based ONLY on the information provided in the snippets.
If the snippets do not contain the answer, say "I cannot answer this question based on the provided documents."

Retrieved Snippets:
{context_str}

Question: {question}
Answer:"""

    answer_text = llm.generate(prompt, context=history_turns)
    
    from app.core.compliance import enforce_ac3
    answer_text = enforce_ac3(answer_text)
    
    new_turns = conversation.turns + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer_text}
    ]
    conversation.turns = new_turns
    
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(conversation, "turns")
    db.commit()
    
    import uuid
    from app.services import audit_service
    audit_service.write_entry(
        db=db,
        actor_user_id=user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id)),
        action_type="rag_query",
        target_entity=f"patient:{patient_id}",
        patient_id=patient_id,
        rationale="Patient record queried via RAG",
        outcome="success",
        context={
            "query": question,
            "citations": citations,
            "provider": "VectorStoreProvider"
        }
    )
    
    return answer_text, citations, conversation.id

async def run_rag_chain(patient_id: str, query: str) -> str:
    from app.core.compliance import enforce_ac3
    answer = "No relevant clinical details found."
    return enforce_ac3(answer)

def query_patient_record(db, patient_id: str, query: str, user_id: str = "00000000-0000-0000-0000-000000000001") -> str:
    from app.core.compliance import enforce_ac3
    answer, _, _ = generate_answer(db, patient_id, query, user_id)
    return enforce_ac3(answer)
