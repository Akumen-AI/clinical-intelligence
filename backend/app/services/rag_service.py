import json
import logging
from typing import List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from app.models.document import Document
from app.models.rag_chunk import PatientRAGChunk

logger = logging.getLogger("app.services.rag_service")

# Basic chunking settings
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


def get_embedding(text: str) -> List[float]:
    """
    Generate an embedding for the given text using google-genai.
    Returns a list of floats.
    """
    from google import genai
    from app.config import settings

    if not settings.GEMINI_API_KEY:
        raise ValueError("[RAG] GEMINI_API_KEY is not set. Cannot generate embeddings.")

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    try:
        response = client.models.embed_content(
            model="gemini-embedding-2",
            contents=text,
        )
        return response.embeddings[0].values
    except Exception as e:
        logger.error(f"[RAG] Failed to generate embedding: {e}")
        raise RuntimeError(f"Failed to generate embedding: {e}") from e


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """
    Split text into overlapping chunks based on characters.
    """
    if not text:
        return []
        
    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        
        # Try to find a clean break near the end (newline or space)
        if end < text_len:
            # Look back up to 50 chars for a newline
            newline_pos = text.rfind('\n', max(start, end - 50), end)
            if newline_pos != -1:
                end = newline_pos + 1
            else:
                # Look back for a space
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
    Chunk and embed the document's OCR text, storing the chunks in the DB.
    """
    if not ocr_text or not document.patient_id:
        return
        
    logger.info(f"[RAG] Indexing document {document.document_id} for patient {document.patient_id}")
    
    # Clean up existing chunks for this document
    db.query(PatientRAGChunk).filter(PatientRAGChunk.source_document_id == document.document_id).delete()
    
    chunks = chunk_text(ocr_text)
    
    for i, chunk_text_content in enumerate(chunks):
        embedding = get_embedding(chunk_text_content)
        if not embedding:
            continue
            
        chunk_record = PatientRAGChunk(
            patient_id=document.patient_id,
            source_document_id=document.document_id,
            content=chunk_text_content,
            embedding=embedding,
            metadata_json={"chunk_index": i, "document_type": getattr(document, "document_type", "Unknown")}
        )
        db.add(chunk_record)
        
    db.commit()
    logger.info(f"[RAG] Successfully indexed {len(chunks)} chunks for document {document.document_id}")


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
        
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm1 = sum(a * a for a in v1) ** 0.5
    norm2 = sum(b * b for b in v2) ** 0.5
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
        
    return dot_product / (norm1 * norm2)


def retrieve_relevant_chunks(db: Session, patient_id: str, query: str, top_k: int = 5) -> List[Tuple[PatientRAGChunk, float]]:
    """
    Retrieve the most relevant chunks for a given query and patient.
    Performs in-memory cosine similarity search since it's scoped to a single patient.
    """
    query_embedding = get_embedding(query)
    if not query_embedding:
        return []
        
    # Get all chunks for this patient
    all_chunks = db.query(PatientRAGChunk).filter(PatientRAGChunk.patient_id == patient_id).all()
    
    from app.config import settings
    scored_chunks = []
    for chunk in all_chunks:
        try:
            # SQLAlchemy JSON column deserializes automatically
            chunk_embedding = chunk.embedding
            score = cosine_similarity(query_embedding, chunk_embedding)
            if score >= settings.RAG_SIMILARITY_THRESHOLD:
                scored_chunks.append((chunk, score))
        except Exception as e:
            logger.warning(f"[RAG] Error processing chunk {chunk.id}: {e}")
            
    # Sort by score descending and take top_k
    scored_chunks.sort(key=lambda x: x[1], reverse=True)
    return scored_chunks[:top_k]


# RBAC NOTE (FR-20): caller is responsible for verifying role before invoking.
# This function performs only patient-scoped retrieval (patient_id filter on
# PatientRAGChunk.patient_id). Role enforcement lives in the router layer via
# require_clinical_read — do not add role checks here.
def generate_answer(db: Session, patient_id: str, question: str, user_id: str, conversation_id: str = None) -> Tuple[str, List[Dict[str, Any]], str]:

    """
    Generate an answer to a user's question based on the patient's retrieved document chunks.
    Returns (answer_text, citations, conversation_id), where citations is a list of structured objects containing:
      - document_id: str
      - snippet: str
      - location: Optional[str]
    """
    from google import genai
    from app.config import settings
    from app.models.rag_conversation import RAGConversation

    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set. Cannot generate answers.")

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    # Handle conversation session
    conversation = None
    if conversation_id:
        conversation = db.query(RAGConversation).filter(RAGConversation.id == conversation_id).first()
        if not conversation or conversation.patient_id != patient_id or conversation.user_id != str(user_id):
            # Strict isolation requirement: if conversation does not match user and patient, deny access
            from app.core.patient_access_guard import AccessDeniedError
            raise AccessDeniedError("Invalid conversation ID for this patient and user.")
    else:
        conversation = RAGConversation(patient_id=patient_id, user_id=str(user_id), turns=[])
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

    # Use the last N turns for context (e.g. up to 10)
    history_turns = conversation.turns[-10:] if conversation.turns else []
    
    # Contextual query rewriting to resolve referential questions
    search_query = question
    if history_turns:
        history_text = "\n".join([f"{t['role'].capitalize()}: {t['content']}" for t in history_turns])
        rewrite_prompt = f"""Given the following conversation history and the latest user question, rewrite the question to be a standalone question that can be understood without the conversation history. Do not answer the question, just rewrite it. If it is already standalone, return it as is.
        
Conversation History:
{history_text}

Latest Question: {question}

Standalone Question:"""
        try:
            rewrite_response = client.models.generate_content(
                model="gemini-3.5-flash",
                contents=rewrite_prompt,
            )
            if rewrite_response.text:
                search_query = rewrite_response.text.strip()
        except Exception as e:
            logger.warning(f"[RAG] Failed to rewrite question for context: {e}")

    # Retrieve top 5 most relevant chunks using the (possibly rewritten) search query
    top_chunks = retrieve_relevant_chunks(db, patient_id, search_query, top_k=5)
    
    if not top_chunks:
        answer_text = "I could not find any relevant information in the patient's documents to answer your question."
        conversation.turns = conversation.turns + [
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer_text}
        ]
        db.commit()
        return answer_text, [], conversation.id
        
    # Build context string and citations list
    context_parts = []
    citations = []
    seen = set()
    
    for i, (chunk, score) in enumerate(top_chunks):
        doc_type = chunk.metadata_json.get("document_type", "Unknown") if chunk.metadata_json else "Unknown"
        context_parts.append(f"--- Document {chunk.source_document_id} ({doc_type}) ---\n{chunk.content}")
        
        # Build location identifier from metadata if available
        location = None
        if chunk.metadata_json and isinstance(chunk.metadata_json, dict):
            if "section" in chunk.metadata_json and chunk.metadata_json["section"]:
                location = str(chunk.metadata_json["section"])
            elif "page_number" in chunk.metadata_json and chunk.metadata_json["page_number"]:
                location = f"Page {chunk.metadata_json['page_number']}"
            elif "page" in chunk.metadata_json and chunk.metadata_json["page"]:
                location = f"Page {chunk.metadata_json['page']}"
            elif "chunk_index" in chunk.metadata_json:
                location = f"Chunk {chunk.metadata_json['chunk_index']}"
            elif doc_type != "Unknown":
                location = doc_type

        chunk_key = (chunk.source_document_id, chunk.content)
        if chunk_key not in seen:
            seen.add(chunk_key)
            citations.append({
                "document_id": chunk.source_document_id,
                "snippet": chunk.content,
                "location": location,
            })
        
    context_str = "\n\n".join(context_parts)
    
    # Build history context for the main prompt
    history_context = ""
    if history_turns:
        history_context = "Conversation History:\n" + "\n".join([f"{t['role'].capitalize()}: {t['content']}" for t in history_turns]) + "\n\n"
    
    prompt = f"""You are a clinical AI assistant answering questions about a specific patient's medical record.
You will be provided with a set of retrieved text snippets from the patient's documents.
Answer the user's question based ONLY on the information provided in the snippets.
If the snippets do not contain the answer, say "I cannot answer this question based on the provided documents."

{history_context}Retrieved Snippets:
{context_str}

Question: {question}
Answer:"""

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
    )
    
    from app.core.compliance import enforce_ac3
    answer_text = response.text
    answer_text = enforce_ac3(answer_text)
    
    # Persist the new turn
    new_turns = conversation.turns + [
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer_text}
    ]
    conversation.turns = new_turns
    
    # SQLAlchemy requires explicit assignment or flag_modified for JSON column mutations
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(conversation, "turns")
    db.commit()
    
    return answer_text, citations, conversation.id


async def run_rag_chain(patient_id: str, query: str) -> str:
    from app.core.compliance import enforce_ac3
    answer = "No relevant clinical details found."
    return enforce_ac3(answer)


def query_patient_record(db, patient_id: str, query: str, user_id: str = "00000000-0000-0000-0000-000000000001") -> str:
    from app.core.compliance import enforce_ac3
    answer, _, _ = generate_answer(db, patient_id, query, user_id)
    return enforce_ac3(answer)


