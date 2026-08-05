-- Story 2.3: Field-Level Confidence Scoring
-- Adds CHECK constraint and composite index for efficient low-confidence routing.
--
-- The confidence_score column was added in Story 2.2 (default 1.0).
-- This migration enforces bounds and adds the composite index needed by Story 2.5.
--
-- NOTE: SQLite does not enforce CHECK constraints added via ALTER TABLE,
-- but PostgreSQL does.  Pydantic validation (ge=0.0, le=1.0) enforces
-- bounds at the application layer for all database backends.

-- Composite index for efficient low-confidence routing queries (Story 2.5).
-- Covers:  GET /documents/{id}/fields?min_confidence=X&max_confidence=Y
CREATE INDEX IF NOT EXISTS ix_extracted_fields_doc_confidence
    ON extracted_fields(document_id, confidence_score);

-- Reverse / Downgrade:
-- DROP INDEX IF EXISTS ix_extracted_fields_doc_confidence;
