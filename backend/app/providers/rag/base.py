from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from enum import Enum


class RetrievalScope(str, Enum):
    PATIENT = "patient"
    POLICY = "policy"


class RAGChunk:
    """A generic RAG chunk independent of the underlying persistence model."""
    def __init__(self, content: str, metadata: Dict[str, Any], embedding: Optional[List[float]] = None, chunk_id: Optional[str] = None):
        self.chunk_id = chunk_id or str(hash(content))
        self.content = content
        self.metadata = metadata
        self.embedding = embedding


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str, context: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Generate text given a prompt and optional conversation history context.
        """
        pass


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """
        Generate vector embeddings for a given text.
        """
        pass


class VectorStoreProvider(ABC):
    @abstractmethod
    def add_chunks(self, scope: RetrievalScope, chunks: List[RAGChunk]) -> None:
        """
        Add chunks to the vector store within the given retrieval scope.
        """
        pass

    @abstractmethod
    def search(self, scope: RetrievalScope, query_vector: List[float], top_k: int, filters: Optional[Dict[str, Any]] = None) -> List[RAGChunk]:
        """
        Search for the top_k most similar chunks within the scope.
        Requires explicit scope boundary to prevent cross-contamination.
        Filters allow scoping down further (e.g. by patient_id within PATIENT scope).
        """
        pass

    @abstractmethod
    def delete_chunks(self, scope: RetrievalScope, filters: Dict[str, Any]) -> None:
        """
        Delete chunks matching filters within a scope.
        """
        pass
