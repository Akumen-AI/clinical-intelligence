"""Self-contained policy-only retrieval and grounded answer generation."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from app.database import SessionLocal
from app.models.policy_rag_chunk import PolicyRAGChunk
from app.providers.rag import get_llm_provider, get_vector_store, RetrievalScope

try:
    from app.config import settings
except ModuleNotFoundError:
    class _EnvironmentSettings:
        AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama")
        OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
    settings = _EnvironmentSettings()


POLICY_NO_GROUNDED_ANSWER = "No grounded answer found in the hospital policy index."


@dataclass(frozen=True)
class PolicyChunkMatch:
    chunk: PolicyRAGChunk
    similarity: float


def retrieve_relevant_policy_chunks(query: str, top_k: int = 5) -> list[PolicyChunkMatch]:
    from app.providers.rag import get_embedding_provider
    embedder = get_embedding_provider()
    query_vector = embedder.embed(query)
    
    if not query_vector:
        return []
        
    vector_store = get_vector_store()
    
    # Strict Boundary: Hardcode RetrievalScope.POLICY
    chunks = vector_store.search(
        scope=RetrievalScope.POLICY,
        query_vector=query_vector,
        top_k=top_k,
        filters=None
    )
    
    # Map back to PolicyRAGChunk format for backwards compatibility with _extractive_answer
    # We create dummy PolicyRAGChunk objects because the vector store returns generic RAGChunks.
    matches = []
    for chunk in chunks:
        doc = PolicyRAGChunk(
            source_document_id=chunk.metadata.get("source_document_id", "Unknown"),
            content=chunk.content,
            metadata_json=chunk.metadata
        )
        matches.append(PolicyChunkMatch(chunk=doc, similarity=chunk.metadata.get("_score", 0.0)))
        
    return matches


def _extractive_answer(query: str, matches: list[PolicyChunkMatch]) -> str:
    """Return a short, readable answer assembled from the best policy sentences."""
    query_terms = set(re.findall(r"[a-z0-9]+", query.lower()))
    candidates = []
    for match in matches:
        for sentence in re.split(r"(?<=[.!?])\s+", match.chunk.content):
            sentence = re.sub(r"^#+\s*", "", sentence).strip()
            if sentence:
                overlap = len(query_terms & set(re.findall(r"[a-z0-9]+", sentence.lower())))
                candidates.append((overlap, match.similarity, sentence))
    ranked = sorted(candidates, key=lambda item: (item[0], item[1]), reverse=True)
    selected = []
    seen = set()
    for _, _, sentence in ranked:
        normalized = sentence.lower()
        if normalized not in seen:
            selected.append(sentence)
            seen.add(normalized)
        if len(selected) == 3:
            break
    return "\n".join(f"• {sentence}" for sentence in selected)


def _call_policy_llm(query: str, context: str) -> str | None:
    """Use the configured LLM provider."""
    if os.getenv("POLICY_LLM_ENABLED", "1").lower() not in {"1", "true", "yes"}:
        return None
        
    prompt = (
        "Answer only from the supplied hospital policy excerpts. Give a concise, readable, LLM-derived answer "
        "in 1-3 short bullet points. Paraphrase and synthesize the relevant policy; do not copy the excerpt "
        "verbatim and do not mention the retrieval process or source markers. "
        "If they do not answer the question, say exactly that no grounded answer was found. "
        f"\nQuestion: {query}\nPolicy excerpts:\n{context}"
    )
    
    try:
        llm = get_llm_provider()
        return llm.generate(prompt)
    except Exception:
        return None


def generate_policy_answer(query: str) -> str:
    matches = retrieve_relevant_policy_chunks(query)
    if not matches:
        return POLICY_NO_GROUNDED_ANSWER
        
    context = "\n\n".join(
        "[Policy source: "
        f"{match.chunk.source_document_id}; "
        f"section: {(match.chunk.metadata_json or {}).get('section_heading', 'Unspecified section')}]\n"
        f"{match.chunk.content}"
        for match in matches
    )
    
    llm_answer = _call_policy_llm(query, context)
    
    if llm_answer and POLICY_NO_GROUNDED_ANSWER.lower() not in llm_answer.lower():
        return llm_answer
        
    return _extractive_answer(query, matches)
