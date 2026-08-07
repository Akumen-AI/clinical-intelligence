import json
import time
import requests
from typing import Optional
from app.config import settings
from app.services.extraction.base import ClinicalFieldExtractor, ExtractionResult
from app.services.extraction.rule_based_extractor import RuleBasedFieldExtractor
from app.schemas.extracted_field import ClinicalFieldsSchema


# Maximum number of attempts before falling back to rule-based extraction.
_MAX_RETRIES = 2
_RETRY_DELAY_SECONDS = 2

# Connect timeout is kept short — if Ollama isn't reachable within 10s,
# retrying won't help. Read timeout is the long pole: the model needs time
# to generate the full structured JSON response.
_CONNECT_TIMEOUT = 10


class OllamaFieldExtractor(ClinicalFieldExtractor):
    def __init__(self, host: str = "http://localhost:11434", model: str = None):
        self.host = host
        self.model = model or settings.OLLAMA_MODEL
        self._fallback_extractor = RuleBasedFieldExtractor()

    def extract(self, text: str, document_type: Optional[str] = None) -> ExtractionResult:
        # Truncate text to 8000 characters to prevent excessive context memory allocation
        truncated_text = text[:8000] if text else ""
        prompt = self._get_prompt(truncated_text, document_type)
        if "qwen3" in self.model.lower():
            prompt = "/no_think\n" + prompt

        read_timeout = settings.OLLAMA_TIMEOUT
        last_exception = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = requests.post(
                    f"{self.host}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                        "options": {
                            "num_thread": 4,
                            "num_ctx": 8192,
                            "temperature": 0.0
                        }
                    },
                    timeout=(_CONNECT_TIMEOUT, read_timeout),
                )
                response.raise_for_status()
                data = response.json()

                raw_response = data.get("response", "").strip()
                if not raw_response:
                    raw_response = data.get("thinking", "").strip()

                if not raw_response:
                    print("[Field Extraction] Ollama returned empty response. Using rule-based fallback.")
                    return self._fallback_extractor.extract(text, document_type)

                result_json = json.loads(raw_response)
                fields = ClinicalFieldsSchema.model_validate(result_json)
                return ExtractionResult(
                    fields=fields,
                    confidence=0.88,
                    field_confidences={
                        k: 0.88 for k, v in fields.model_dump().items() if v is not None
                    },
                )
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                last_exception = e
                if attempt < _MAX_RETRIES:
                    print(
                        f"[Field Extraction] Ollama attempt {attempt}/{_MAX_RETRIES} failed: {e}. "
                        f"Retrying in {_RETRY_DELAY_SECONDS}s..."
                    )
                    time.sleep(_RETRY_DELAY_SECONDS)
                else:
                    print(
                        f"[Field Extraction] Ollama extraction failed after {_MAX_RETRIES} attempts: {e}. "
                        f"Using rule-based fallback."
                    )
            except Exception as e:
                # Non-retryable errors (JSON parse, validation, etc.) — fail fast
                print(f"[Field Extraction] Ollama extraction failed: {e}. Using rule-based fallback.")
                return self._fallback_extractor.extract(text, document_type)

        return self._fallback_extractor.extract(text, document_type)
