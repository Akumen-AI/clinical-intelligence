from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    AI_PROVIDER: str = "ollama"
    OLLAMA_MODEL: str = "qwen3:4b"
    GEMINI_API_KEY: str = ""
    DOCUMENT_CLASSIFICATION_THRESHOLD: float = 0.80
    CONFIDENCE_THRESHOLD: float = 0.80  # Default confidence threshold for routing extracted fields (Story 2.5: default 0.80)
    OLLAMA_TIMEOUT: int = 120  # seconds — read timeout for Ollama API calls
    OCR_PAGE_TIMEOUT: int = 120  # seconds — per-page timeout for OCR subprocess

settings = Settings()

