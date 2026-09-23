"""CLI ingestion for markdown/text hospital policy documents only."""

from __future__ import annotations

import structlog
logger = structlog.get_logger(__name__)

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

from app.database import Base, SessionLocal, engine
from app.providers.rag import get_embedding_provider, get_vector_store, RetrievalScope, RAGChunk


DEFAULT_POLICY_DOCUMENTS_DIR = (
    Path(__file__).resolve().parents[2] / "data" / "policy_documents"
)
_SECTION_RE = re.compile(r"(?=^##\s+Section\s+\d+\s*$)", re.MULTILINE | re.IGNORECASE)


def _split_sections(text: str) -> Iterable[tuple[str, str]]:
    parts = [part.strip() for part in _SECTION_RE.split(text) if part.strip()]
    for index, part in enumerate(parts):
        lines = part.splitlines()
        heading = lines[0].strip() if lines else f"Section {index + 1}"
        yield heading, part


def ingest_policy_documents(
    documents_dir: Path | str = DEFAULT_POLICY_DOCUMENTS_DIR,
) -> int:
    """Replace the policy index with chunks from local .md/.txt policy files."""
    documents_path = Path(documents_dir)
    documents_path.mkdir(parents=True, exist_ok=True)

    files = sorted(
        path for path in documents_path.iterdir()
        if path.is_file() and path.suffix.lower() in {".md", ".txt"}
    )
    count = 0
    
    vector_store = get_vector_store()
    embedder = get_embedding_provider()
    
    try:
        # We delete all existing policy chunks to rebuild the index
        # We can simulate a wipe by deleting with an empty filter, but our FAISS implementation
        # only deletes matching filters. To wipe all, we clear the list.
        # But for safety, we just re-initialize the store's policy scope.
        vector_store.chunks_store[RetrievalScope.POLICY] = []
        vector_store._rebuild_index(RetrievalScope.POLICY)
        
        chunks_to_add = []
        for path in files:
            text = path.read_text(encoding="utf-8")
            for chunk_index, (heading, content) in enumerate(_split_sections(text)):
                embedding = embedder.embed(content)
                if embedding:
                    chunks_to_add.append(RAGChunk(
                        content=content,
                        embedding=embedding,
                        metadata={
                            "source_document_id": path.name,
                            "section_heading": heading,
                            "chunk_index": chunk_index,
                        }
                    ))
                    count += 1
                    
        if chunks_to_add:
            vector_store.add_chunks(RetrievalScope.POLICY, chunks_to_add)
            
        return count
    except Exception as e:
        logger.info(f"Error during ingestion: {e}")
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild the hospital policy RAG index")
    parser.add_argument("--documents-dir", type=Path, default=DEFAULT_POLICY_DOCUMENTS_DIR)
    args = parser.parse_args()
    logger.info(json.dumps({"chunks_ingested": ingest_policy_documents(args.documents_dir)}))


if __name__ == "__main__":
    main()
