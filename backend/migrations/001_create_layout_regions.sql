CREATE TABLE IF NOT EXISTS layout_regions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id VARCHAR(36) NOT NULL,
    region_type VARCHAR(50) NOT NULL,
    bbox JSON NOT NULL,
    confidence FLOAT NOT NULL,
    created_at DATETIME NOT NULL,
    CONSTRAINT fk_layout_regions_document
        FOREIGN KEY (document_id) REFERENCES documents(document_id)
        ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_layout_regions_document_id
    ON layout_regions(document_id);
