import faiss
import numpy as np
from typing import Any, Dict, List, Optional
import os
import pickle

from .base import VectorStoreProvider, RAGChunk, RetrievalScope

class FaissVectorStoreProvider(VectorStoreProvider):
    def __init__(self, data_dir: str = "data/vector_store"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
        # A dictionary mapping scope -> FAISS index
        self.indexes: Dict[RetrievalScope, faiss.Index] = {}
        # A dictionary mapping scope -> list of RAGChunks (the metadata store)
        self.chunks_store: Dict[RetrievalScope, List[RAGChunk]] = {
            RetrievalScope.PATIENT: [],
            RetrievalScope.POLICY: []
        }
        
        self._load()

    def _get_path(self, scope: RetrievalScope) -> str:
        return os.path.join(self.data_dir, f"{scope.value}_store.pkl")

    def _load(self):
        for scope in RetrievalScope:
            path = self._get_path(scope)
            if os.path.exists(path):
                with open(path, "rb") as f:
                    self.chunks_store[scope] = pickle.load(f)
            self._rebuild_index(scope)

    def _save(self, scope: RetrievalScope):
        path = self._get_path(scope)
        with open(path, "wb") as f:
            pickle.dump(self.chunks_store[scope], f)

    def _rebuild_index(self, scope: RetrievalScope):
        chunks = self.chunks_store[scope]
        if not chunks:
            self.indexes[scope] = None
            return
            
        dim = len(chunks[0].embedding)
        index = faiss.IndexHNSWFlat(dim, 32)  # HNSW for better performance at scale
        
        embeddings = np.array([c.embedding for c in chunks], dtype=np.float32)
        # Normalize vectors for cosine similarity
        faiss.normalize_L2(embeddings)
        index.add(embeddings)
        
        self.indexes[scope] = index

    def add_chunks(self, scope: RetrievalScope, chunks: List[RAGChunk]) -> None:
        if not chunks:
            return
            
        # Optional validation
        for c in chunks:
            if not c.embedding:
                raise ValueError("Chunk must have an embedding to be added to the vector store.")
                
        self.chunks_store[scope].extend(chunks)
        self._rebuild_index(scope)
        self._save(scope)

    def search(self, scope: RetrievalScope, query_vector: List[float], top_k: int, filters: Optional[Dict[str, Any]] = None) -> List[RAGChunk]:
        index = self.indexes.get(scope)
        if not index or index.ntotal == 0:
            return []

        q = np.array([query_vector], dtype=np.float32)
        faiss.normalize_L2(q)
        
        # We fetch more than top_k initially to account for filtering
        fetch_k = min(index.ntotal, top_k * 10 if filters else top_k)
        
        scores, I = index.search(q, fetch_k)
        
        results = []
        for i in range(len(I[0])):
            idx = I[0][i]
            if idx == -1:
                break
                
            chunk = self.chunks_store[scope][idx]
            
            # Apply filters
            if filters:
                match = True
                for k, v in filters.items():
                    if chunk.metadata.get(k) != v:
                        match = False
                        break
                if not match:
                    continue
                    
            # We attach the score to metadata temporarily for the caller to use if needed
            chunk.metadata["_score"] = float(scores[0][i])
            results.append(chunk)
            
            if len(results) >= top_k:
                break
                
        return results

    def delete_chunks(self, scope: RetrievalScope, filters: Dict[str, Any]) -> None:
        if not filters:
            return
            
        original_len = len(self.chunks_store[scope])
        
        # Keep chunks that DO NOT match the filters
        new_chunks = []
        for chunk in self.chunks_store[scope]:
            match = True
            for k, v in filters.items():
                if chunk.metadata.get(k) != v:
                    match = False
                    break
            if not match:
                new_chunks.append(chunk)
                
        if len(new_chunks) != original_len:
            self.chunks_store[scope] = new_chunks
            self._rebuild_index(scope)
            self._save(scope)

