from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    AI_PROVIDER: str = "ollama"
    OLLAMA_MODEL: str = "qwen3:4b"
    GEMINI_API_KEY: str = ""
    DOCUMENT_CLASSIFICATION_THRESHOLD: float = 0.80
    CONFIDENCE_THRESHOLD: float = 0.80  # Default confidence threshold for routing extracted fields (Story 2.5: default 0.80)
    RAG_SIMILARITY_THRESHOLD: float = 0.5  # Similarity threshold for RAG chunks
    OLLAMA_TIMEOUT: int = 120  # seconds — read timeout for Ollama API calls
    OCR_PAGE_TIMEOUT: int = 120  # seconds — per-page timeout for OCR subprocess

    # --- Handwriting Extraction Settings ---
    # Enable/disable the handwriting extraction path (requires GEMINI_API_KEY)
    HANDWRITING_EXTRACTION_ENABLED: bool = True
    # Per-fragment OCR confidence threshold: fragments scoring below this are
    # considered "low confidence" (printed text typically scores 0.9+, while
    # PaddleOCR on handwritten text typically scores between 0.70 and 0.84).
    HANDWRITING_OCR_CONFIDENCE_THRESHOLD: float = 0.85
    # Proportion of fragments below the confidence threshold required to
    # trigger handwriting routing. E.g., 0.15 means >15% low-confidence
    # fragments triggers the handwriting path (avoids dilution by printed letterheads).
    HANDWRITING_LOW_CONFIDENCE_PROPORTION: float = 0.15
    # Minimum consecutive low-confidence fragments to trigger handwriting routing
    # regardless of overall page proportion (e.g. 3 consecutive handwritten Rx lines).
    HANDWRITING_CONSECUTIVE_LOW_CONFIDENCE_COUNT: int = 3

settings = Settings()

