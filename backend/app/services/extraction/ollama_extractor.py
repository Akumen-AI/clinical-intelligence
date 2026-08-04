import json
import requests
from typing import Optional
from app.config import settings
from app.services.extraction.base import ClinicalFieldExtractor, ExtractionResult
from app.services.extraction.rule_based_extractor import RuleBasedFieldExtractor
from app.schemas.extracted_field import ClinicalFieldsSchema


class OllamaFieldExtractor(ClinicalFieldExtractor):
    def __init__(self, host: str = "http://localhost:11434", model: str = None):
        self.host = host
        self.model = model or settings.OLLAMA_MODEL
        self._fallback_extractor = RuleBasedFieldExtractor()

    def extract(self, text: str, document_type: Optional[str] = None) -> ExtractionResult:
        prompt = self._get_prompt(text, document_type)
        if "qwen3" in self.model.lower():
            prompt = "/no_think\n" + prompt

        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                },
                timeout=60,
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
        except Exception as e:
            print(f"[Field Extraction] Ollama extraction failed: {e}. Using rule-based fallback.")
            return self._fallback_extractor.extract(text, document_type)
