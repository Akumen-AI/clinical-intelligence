from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    AI_PROVIDER: str = "ollama"
    OLLAMA_MODEL: str = "qwen3:4b"
    GEMINI_API_KEY: str = ""
    DOCUMENT_CLASSIFICATION_THRESHOLD: float = 0.80

settings = Settings()

