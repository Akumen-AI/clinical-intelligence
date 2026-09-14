from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent.parent / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ENV_FILE), env_file_encoding="utf-8", extra="ignore")

    AI_PROVIDER: str = "ollama"
    OLLAMA_MODEL: str = "qwen3:4b"
    GEMINI_API_KEY: str = ""
    DOCUMENT_CLASSIFICATION_THRESHOLD: float = 0.80
    CONFIDENCE_THRESHOLD: float = 0.80  # Default confidence threshold for routing extracted fields
    RAG_SIMILARITY_THRESHOLD: float = 0.5  # Similarity threshold for RAG chunks
    OLLAMA_TIMEOUT: int = 120  # seconds — read timeout for Ollama API calls
    OCR_PAGE_TIMEOUT: int = 120  # seconds — per-page timeout for OCR subprocess

    # --- Handwriting Extraction Settings ---
    HANDWRITING_EXTRACTION_ENABLED: bool = True
    HANDWRITING_OCR_CONFIDENCE_THRESHOLD: float = 0.85
    HANDWRITING_LOW_CONFIDENCE_PROPORTION: float = 0.15
    HANDWRITING_CONSECUTIVE_LOW_CONFIDENCE_COUNT: int = 3

settings = Settings()
