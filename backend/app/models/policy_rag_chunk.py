"""Database model for the isolated hospital-policy RAG index."""

from sqlalchemy import JSON, Column, Integer, String, Text

from app.database import Base


class PolicyRAGChunk(Base):
    __tablename__ = "policy_rag_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_document_id = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    # JSON keeps this model portable across the existing SQLite and SQL databases.
    embedding = Column(JSON, nullable=False)
    metadata_json = Column(JSON, nullable=False, default=dict)

