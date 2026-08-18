"""Self-contained policy-only retrieval and grounded answer generation."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import urllib.request
from dataclasses import dataclass

from app.database import SessionLocal
from app.models.policy_rag_chunk import PolicyRAGChunk

try:
    from app.config import settings
except ModuleNotFoundError:
    # Keeps isolated policy retrieval usable in minimal test environments.
    class _EnvironmentSettings:
        AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama")
        OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
        OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))

    settings = _EnvironmentSettings()


POLICY_NO_GROUNDED_ANSWER = "No grounded answer found in the hospital policy index."
POLICY_SIMILARITY_THRESHOLD = 0.20


@dataclass(frozen=True)
class PolicyChunkMatch:
    chunk: PolicyRAGChunk
    similarity: float


def _embed(text: str, dimensions: int = 256) -> list[float]:
    vector = [0.0] * dimensions
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        index = int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big") % dimensions
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def retrieve_relevant_policy_chunks(query: str, top_k: int = 5) -> list[PolicyChunkMatch]:
    query_vector = _embed(query)
    db = SessionLocal()
    try:
        matches = [
            PolicyChunkMatch(chunk, _cosine(query_vector, list(chunk.embedding or [])))
            for chunk in db.query(PolicyRAGChunk).all()
        ]
        return [
            match for match in sorted(matches, key=lambda item: item.similarity, reverse=True)[:top_k]
            if match.similarity >= POLICY_SIMILARITY_THRESHOLD
        ]
    finally:
        db.close()


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
    """Use the same configured provider/model as the rest of the platform."""
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
        if settings.AI_PROVIDER.lower() == "gemini" and settings.GEMINI_API_KEY:
            from google import genai

            response = genai.Client(api_key=settings.GEMINI_API_KEY).models.generate_content(
                model="gemini-3.5-flash",
                contents=prompt,
            )
            return (response.text or "").strip() or None

        model = os.getenv("POLICY_LLM_MODEL", settings.OLLAMA_MODEL)
        ollama_prompt = f"/no_think\n{prompt}" if "qwen3" in model.lower() else prompt
        payload = json.dumps({
                "model": model,
                "stream": False,
                "prompt": ollama_prompt,
                "options": {"temperature": 0.0},
            }).encode("utf-8")
        request = urllib.request.Request(
            os.getenv("POLICY_LLM_URL", "http://localhost:11434/api/generate"),
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=min(3, settings.OLLAMA_TIMEOUT)) as response:
            return json.loads(response.read().decode("utf-8")).get("response", "").strip() or None
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
    # The prompt constrains the model to the retrieved policy context. A model-derived
    # answer is preferred; extraction is only a safe availability fallback.
    if llm_answer and POLICY_NO_GROUNDED_ANSWER.lower() not in llm_answer.lower():
        return llm_answer
    return _extractive_answer(query, matches)
