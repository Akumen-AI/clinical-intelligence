import json
import logging
import uuid
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.extracted_field import ExtractedField, VerificationStatus
from app.providers.rag import get_llm_provider, get_embedding_provider, get_vector_store, RetrievalScope, RAGChunk

logger = logging.getLogger("app.services.rag_service")

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
SIMILARITY_THRESHOLD = 0.6  # Adjust based on embedding model and use case

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
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
    if not document.patient_id:
        return
        
    logger.info(f"[RAG] Indexing document {document.document_id} for patient {document.patient_id}")
    vector_store = get_vector_store()
    embedder = get_embedding_provider()
    
    vector_store.delete_chunks(RetrievalScope.PATIENT, filters={"source_document_id": document.document_id})
    chunks = []
    
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
                    "document_type": getattr(document, "document_type", "Unknown"),
                    "document_revision": document.document_version,
                    "bounding_box": json.dumps(field.bounding_box) if field.bounding_box else None
                }
            ))

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
                    "document_revision": document.document_version,
                    "type": "ocr_text"
                }
            ))
            
    vector_store.add_chunks(RetrievalScope.PATIENT, chunks)

def retrieve_relevant_chunks(db: Session, patient_id: str, query: str, top_k: int = 5) -> List[Tuple[RAGChunk, float]]:
    embedder = get_embedding_provider()
    vector_store = get_vector_store()
    
    query_embedding = embedder.embed(query)
    if not query_embedding:
        return []
        
    chunks = vector_store.search(
        scope=RetrievalScope.PATIENT,
        query_vector=query_embedding,
        top_k=top_k * 2,  # Fetch more to allow threshold filtering
        filters={"patient_id": patient_id}
    )
    
    results = []
    for chunk in chunks:
        score = chunk.metadata.get("_score", 0.0)
        if score >= SIMILARITY_THRESHOLD:
            results.append((chunk, score))
            if len(results) >= top_k:
                break
                
    return results

def generate_answer(db: Session, patient_id: str, question: str, user_id: str, conversation_id: str = None) -> Tuple[str, List[Dict[str, Any]], str]:
    from app.models.rag_conversation import RAGConversation
    from app.models.rag_message import RAGMessage
    from app.core.compliance import enforce_ac3
    
    llm = get_llm_provider()
    
    # Authenticate user and resolve authorization scope
    if conversation_id:
        conversation = db.query(RAGConversation).filter(RAGConversation.id == conversation_id).first()
        if not conversation or conversation.patient_id != patient_id or conversation.user_id != str(user_id):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Invalid conversation ID for this patient and user.")
    else:
        conversation = RAGConversation(patient_id=patient_id, user_id=str(user_id))
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Use RAGMessage for append-only history
    history = db.query(RAGMessage).filter(RAGMessage.conversation_id == conversation.id).order_by(RAGMessage.created_at.asc()).all()
    history_turns = [{"role": msg.role, "content": msg.content} for msg in history[-10:]] if history else []
    
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
    
    def _save_turn(role: str, content: str):
        msg = RAGMessage(conversation_id=conversation.id, role=role, content=content)
        db.add(msg)
        db.commit()

    _save_turn("user", question)
    
    if not top_chunks:
        answer_text = "I could not find any relevant information in the patient's documents to answer your question."
        _save_turn("assistant", answer_text)
        return answer_text, [], conversation.id
        
    context_parts = []
    chunk_map = {}
    
    for i, (chunk, score) in enumerate(top_chunks):
        chunk_identifier = f"chunk_{i}"
        chunk_map[chunk_identifier] = chunk
        
        doc_type = chunk.metadata.get("document_type", "Unknown") if chunk.metadata else "Unknown"
        doc_id = chunk.metadata.get("source_document_id", "Unknown")
        context_parts.append(f"--- Chunk ID: {chunk_identifier} | Document {doc_id} ({doc_type}) ---\n{chunk.content}")
        
    context_str = "\n\n".join(context_parts)
    
    prompt = f"""You are a clinical AI assistant answering questions about a specific patient's medical record.
You will be provided with a set of retrieved text snippets (chunks) from the patient's documents.
Answer the user's question based ONLY on the information provided in the snippets.

You MUST output your response as a valid JSON object matching this exact schema:
{{
  "is_grounded": true or false,
  "answer": "Your detailed answer here.",
  "citations": [
    {{"chunk_id": "chunk_0"}},
    {{"chunk_id": "chunk_1"}}
  ]
}}

Rules:
1. If the snippets do not contain enough information to fully answer the question, set "is_grounded" to false and say so in the "answer".
2. You must ONLY use the provided chunks.
3. Your "citations" array must contain the EXACT "chunk_id" values (e.g. "chunk_0") that you used to form the answer.

Retrieved Snippets:
{context_str}

Question: {question}
"""

    # We use our LLM Provider, expecting JSON back.
    llm_response = llm.generate(prompt, context=history_turns)
    
    # Strip markdown codeblocks if LLM adds them
    llm_response = llm_response.strip()
    if llm_response.startswith("```json"):
        llm_response = llm_response[7:-3].strip()
    elif llm_response.startswith("```"):
        llm_response = llm_response[3:-3].strip()
        
    answer_text = "I could not find any relevant information to answer your question (No grounded answer)."
    citations = []
    
    try:
        parsed = json.loads(llm_response)
        
        if not parsed.get("is_grounded"):
            answer_text = parsed.get("answer", answer_text)
        else:
            answer_text = parsed.get("answer", answer_text)
            
            # Deterministic Verification: Check that every cited chunk actually exists in our retrieved context
            valid_citations = set()
            for citation in parsed.get("citations", []):
                cid = citation.get("chunk_id")
                if cid in chunk_map:
                    valid_citations.add(cid)
            
            if not valid_citations:
                # The LLM hallucinated citations or failed to cite anything while claiming to be grounded
                answer_text = "I cannot confidently answer this question as my verification step found insufficient supporting evidence (No grounded answer)."
            else:
                seen = set()
                for cid in valid_citations:
                    chunk = chunk_map[cid]
                    
                    doc_id = chunk.metadata.get("source_document_id", "Unknown")
                    content = chunk.content
                    chunk_key = (doc_id, content)
                    
                    if chunk_key not in seen:
                        seen.add(chunk_key)
                        
                        doc_type = chunk.metadata.get("document_type")
                        
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
                            elif doc_type and doc_type != "Unknown":
                                location = doc_type
                        
                        citations.append({
                            "document_id": doc_id,
                            "snippet": content,
                            "document_type": doc_type,
                            "page": str(chunk.metadata.get("page", chunk.metadata.get("page_number", ""))) or None,
                            "source_field_id": chunk.metadata.get("source_field_id"),
                            "document_revision": chunk.metadata.get("document_revision"),
                            "bounding_box": chunk.metadata.get("bounding_box"),
                            "location": location,
                        })

    except json.JSONDecodeError:
        logger.error(f"[RAG] Failed to parse structured LLM output: {llm_response}")
        answer_text = "I encountered an error formatting my response. Please try asking again."
    
    answer_text = enforce_ac3(answer_text)
    
    _save_turn("assistant", answer_text)
    
    from app.services import audit_service
    audit_service.write_entry(
        db=db,
        actor_user_id=user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id)),
        action_type="rag_query",
        target_entity=f"patient:{patient_id}",
        patient_id=patient_id,
        rationale=f"RAG query grounded: {bool(citations)}",
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
