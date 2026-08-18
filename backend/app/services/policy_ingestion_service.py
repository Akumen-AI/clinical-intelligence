"""CLI ingestion for markdown/text hospital policy documents only."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Iterable

from app.database import Base, SessionLocal, engine
from app.models.policy_rag_chunk import PolicyRAGChunk


DEFAULT_POLICY_DOCUMENTS_DIR = (
    Path(__file__).resolve().parents[2] / "data" / "policy_documents"
)
_SECTION_RE = re.compile(r"(?=^##\s+Section\s+\d+\s*$)", re.MULTILINE | re.IGNORECASE)


def _embed(text: str, dimensions: int = 256) -> list[float]:
    """Create a deterministic, dependency-free normalized bag-of-words embedding."""
    import hashlib
    import math

    vector = [0.0] * dimensions
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest, "big") % dimensions
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector] if norm else vector


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
    Base.metadata.create_all(bind=engine, tables=[PolicyRAGChunk.__table__])

    files = sorted(
        path for path in documents_path.iterdir()
        if path.is_file() and path.suffix.lower() in {".md", ".txt"}
    )
    db = SessionLocal()
    count = 0
    try:
        db.query(PolicyRAGChunk).delete(synchronize_session=False)
        for path in files:
            text = path.read_text(encoding="utf-8")
            for chunk_index, (heading, content) in enumerate(_split_sections(text)):
                db.add(
                    PolicyRAGChunk(
                        source_document_id=path.name,
                        content=content,
                        embedding=_embed(content),
                        metadata_json={
                            "section_heading": heading,
                            "chunk_index": chunk_index,
                        },
                    )
                )
                count += 1
        db.commit()
        return count
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild the hospital policy RAG index")
    parser.add_argument("--documents-dir", type=Path, default=DEFAULT_POLICY_DOCUMENTS_DIR)
    args = parser.parse_args()
    print(json.dumps({"chunks_ingested": ingest_policy_documents(args.documents_dir)}))


if __name__ == "__main__":
    main()
