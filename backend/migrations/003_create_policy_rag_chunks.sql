-- Isolated policy-only RAG index.
-- source_document_id is a filename, intentionally not a foreign key.
CREATE TABLE IF NOT EXISTS policy_rag_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_document_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    embedding JSON NOT NULL,
    metadata_json JSON NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_policy_rag_chunks_source_document_id
    ON policy_rag_chunks (source_document_id);
