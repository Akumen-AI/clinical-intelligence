from typing import Dict, List, Optional
from google import genai
from .base import LLMProvider, EmbeddingProvider
import logging

logger = logging.getLogger(__name__)

class GeminiLLMProvider(LLMProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-3.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def generate(self, prompt: str, context: Optional[List[Dict[str, str]]] = None) -> str:
        final_prompt = prompt
        if context:
            history_text = "\n".join([f"{t['role'].capitalize()}: {t['content']}" for t in context])
            final_prompt = f"Conversation History:\n{history_text}\n\n{prompt}"
            
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=final_prompt,
            )
            return response.text or ""
        except Exception as e:
            logger.error(f"[GeminiLLMProvider] Generation failed: {e}")
            raise


class GeminiEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model_name: str = "gemini-embedding-2"):
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name

    def embed(self, text: str) -> List[float]:
        if not text:
            return []
            
        try:
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=text,
            )
            return response.embeddings[0].values
        except Exception as e:
            logger.error(f"[GeminiEmbeddingProvider] Embedding failed: {e}")
            raise
