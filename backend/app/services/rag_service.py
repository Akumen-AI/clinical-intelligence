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
            
        start = end - overlap
        
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


def generate_answer(db: Session, patient_id: str, question: str) -> Tuple[str, List[str]]:
    """
    Generate an answer to a user's question based on the patient's retrieved document chunks.
    """
    from google import genai
    from app.config import settings

    if not settings.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set. Cannot generate answers.")

    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    
    # Retrieve top 5 most relevant chunks
    top_chunks = retrieve_relevant_chunks(db, patient_id, question, top_k=5)
    
    if not top_chunks:
        return "I could not find any relevant information in the patient's documents to answer your question.", []
        
    # Build context string
    context_parts = []
    source_documents = set()
    
    for i, (chunk, score) in enumerate(top_chunks):
        source_documents.add(chunk.source_document_id)
        doc_type = chunk.metadata_json.get("document_type", "Unknown") if chunk.metadata_json else "Unknown"
        context_parts.append(f"--- Document {chunk.source_document_id} ({doc_type}) ---\n{chunk.content}")
        
    context_str = "\n\n".join(context_parts)
    
    prompt = f"""You are a clinical AI assistant answering questions about a specific patient's medical record.
You will be provided with a set of retrieved text snippets from the patient's documents.
Answer the user's question based ONLY on the information provided in the snippets.
If the snippets do not contain the answer, say "I cannot answer this question based on the provided documents."

Retrieved Snippets:
{context_str}

Question: {question}
Answer:"""

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    
    return response.text, list(source_documents)
