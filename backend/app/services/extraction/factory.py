import requests
from app.config import settings
from app.services.extraction.base import ClinicalFieldExtractor
from app.services.extraction.rule_based_extractor import RuleBasedFieldExtractor
from app.services.extraction.ollama_extractor import OllamaFieldExtractor


def _is_ollama_available(host: str = "http://localhost:11434") -> bool:
    """Check if Ollama is running and reachable."""
    try:
        resp = requests.get(f"{host}/api/tags", timeout=3)
        return resp.status_code == 200
    except Exception:
        return False


def get_field_extractor() -> ClinicalFieldExtractor:
    """
    Returns the best available field extractor.
    Strategy: Try configured provider -> Ollama (if available) -> Gemini -> Rule-based fallback.
    """
    provider = settings.AI_PROVIDER.lower()

    if provider == "gemini":
        if settings.GEMINI_API_KEY:
            print("[Field Extraction] Using Gemini field extractor.")
            from app.services.extraction.gemini_extractor import GeminiFieldExtractor
            return GeminiFieldExtractor()
        else:
            print("[Field Extraction] Gemini configured but GEMINI_API_KEY not set. Using Rule-based extractor.")
            return RuleBasedFieldExtractor()

    if _is_ollama_available():
        print("[Field Extraction] Using Ollama field extractor (local model detected).")
        return OllamaFieldExtractor()

    if settings.GEMINI_API_KEY:
        print("[Field Extraction] Ollama not available. Falling back to Gemini field extractor.")
        from app.services.extraction.gemini_extractor import GeminiFieldExtractor
        return GeminiFieldExtractor()

    print("[Field Extraction] Neither Ollama nor Gemini available. Using Rule-based field extractor.")
    return RuleBasedFieldExtractor()
