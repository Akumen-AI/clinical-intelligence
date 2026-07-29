import requests
import json
from app.config import settings
from app.services.classification.base import DocumentClassifier, ClassificationResult

class OllamaClassifier(DocumentClassifier):
    def __init__(self, host: str = "http://localhost:11434", model: str = None):
        self.host = host
        self.model = model or settings.OLLAMA_MODEL

    def classify(self, text: str) -> ClassificationResult:
        prompt = self._get_prompt(text)
        # Disable thinking mode only for models that enable it by default (e.g. qwen3)
        if "qwen3" in self.model.lower():
            prompt = "/no_think\n" + prompt

        try:
            response = requests.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json"
                },
                timeout=60
            )
            response.raise_for_status()
            data = response.json()

            # qwen3 thinking models may put output in 'thinking' field
            # with an empty 'response'. Check 'response' first, fall back to 'thinking'.
            raw_response = data.get("response", "").strip()
            if not raw_response:
                raw_response = data.get("thinking", "").strip()

            if not raw_response:
                print(f"Ollama returned empty response and thinking fields.")
                return ClassificationResult(document_type="Unknown", confidence=0.0)

            result_json = json.loads(raw_response)

            return ClassificationResult(
                document_type=result_json.get("document_type", "Unknown"),
                confidence=float(result_json.get("confidence", 0.0))
            )
        except Exception as e:
            print(f"Ollama classification failed: {e}")
            return ClassificationResult(document_type="Unknown", confidence=0.0)

