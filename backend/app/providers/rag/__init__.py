import os
from .base import LLMProvider, EmbeddingProvider, VectorStoreProvider, RetrievalScope, RAGChunk
from .faiss_provider import FaissVectorStoreProvider

# We can initialize the vector store as a singleton
vector_store = FaissVectorStoreProvider()

def get_llm_provider() -> LLMProvider:
    from app.config import settings
    if settings.AI_PROVIDER.lower() == "gemini" and settings.GEMINI_API_KEY:
        from .gemini_provider import GeminiLLMProvider
        return GeminiLLMProvider(api_key=settings.GEMINI_API_KEY)
        
    # Fallback to a mock/ollama provider (for tests)
    class DummyLLM(LLMProvider):
        def generate(self, prompt: str, context=None) -> str:
            return "This is a dummy response."
    return DummyLLM()

def get_embedding_provider() -> EmbeddingProvider:
    from app.config import settings
    if settings.AI_PROVIDER.lower() == "gemini" and settings.GEMINI_API_KEY:
        from .gemini_provider import GeminiEmbeddingProvider
        return GeminiEmbeddingProvider(api_key=settings.GEMINI_API_KEY)
        
    class DummyEmbed(EmbeddingProvider):
        def embed(self, text: str) -> list[float]:
            import hashlib
            import math
            dimensions = 256
            vector = [0.0] * dimensions
            for token in text.split():
                index = int.from_bytes(hashlib.blake2b(token.encode(), digest_size=8).digest(), "big") % dimensions
                vector[index] += 1.0
            norm = math.sqrt(sum(value * value for value in vector))
            return [value / norm for value in vector] if norm else vector
    return DummyEmbed()

def get_vector_store() -> VectorStoreProvider:
    return vector_store
