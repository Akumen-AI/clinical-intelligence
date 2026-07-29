import json
from google import genai
from app.config import settings
from app.services.classification.base import DocumentClassifier, ClassificationResult

class GeminiClassifier(DocumentClassifier):
    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be set to use GeminiClassifier")
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = "gemini-2.5-flash"

    def classify(self, text: str) -> ClassificationResult:
        prompt = self._get_prompt(text)
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                ),
            )
            
            result_json = json.loads(response.text)
            
            return ClassificationResult(
                document_type=result_json.get("document_type", "Unknown"),
                confidence=float(result_json.get("confidence", 0.0))
            )
        except Exception as e:
            print(f"Gemini classification failed: {e}")
            return ClassificationResult(document_type="Unknown", confidence=0.0)
