import requests
from app.config import settings
from app.services.classification.base import DocumentClassifier
from app.services.classification.ollama_classifier import OllamaClassifier
from app.services.classification.gemini_classifier import GeminiClassifier


def _is_ollama_available(host: str = "http://localhost:11434") -> bool:
    """Check if Ollama is running and reachable."""
    try:
        resp = requests.get(f"{host}/api/tags", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def get_document_classifier() -> DocumentClassifier:
    """
    Returns the best available classifier.
    Strategy: Try Ollama first (local), fall back to Gemini if Ollama is unavailable.
    """
    provider = settings.AI_PROVIDER.lower()

    if provider == "gemini":
        # Explicitly configured for Gemini
        print("[Classification] Using Gemini classifier (configured via AI_PROVIDER).")
        return GeminiClassifier()

    # Default / "ollama" provider: try Ollama first, fall back to Gemini
    if _is_ollama_available():
        print("[Classification] Using Ollama classifier (local model detected).")
        return OllamaClassifier()

    # Ollama not available — try Gemini as fallback
    if settings.GEMINI_API_KEY:
        print("[Classification] Ollama not available. Falling back to Gemini classifier.")
        return GeminiClassifier()

    print("[Classification] WARNING: No classifier available. Ollama is not running and GEMINI_API_KEY is not set.")
    # Return Ollama anyway; it will fail gracefully with Unknown/0.0
    return OllamaClassifier()

