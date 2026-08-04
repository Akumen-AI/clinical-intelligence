import json
from typing import Optional
from google import genai
from app.config import settings
from app.services.extraction.base import ClinicalFieldExtractor, ExtractionResult
from app.services.extraction.rule_based_extractor import RuleBasedFieldExtractor
from app.schemas.extracted_field import ClinicalFieldsSchema


class GeminiFieldExtractor(ClinicalFieldExtractor):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be set to use GeminiFieldExtractor")
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-3.5-flash"
        self._fallback_extractor = RuleBasedFieldExtractor()

    def extract(self, text: str, document_type: Optional[str] = None) -> ExtractionResult:
        prompt = self._get_prompt(text, document_type)
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            raw_text = response.text or ""
            data = json.loads(raw_text)
            fields = ClinicalFieldsSchema.model_validate(data)
            return ExtractionResult(
                fields=fields,
                confidence=0.92,
                field_confidences={
                    k: 0.92 for k, v in fields.model_dump().items() if v is not None
                },
            )
        except Exception as e:
            print(f"[Field Extraction] Gemini extractor failed: {e}. Using rule-based fallback.")
            return self._fallback_extractor.extract(text, document_type)
