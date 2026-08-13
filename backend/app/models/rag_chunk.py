import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, String, Text, DateTime, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship

from app.database import Base


class PatientRAGChunk(Base):
    """
    Stores text chunks and their embeddings for a specific patient.
    Embeddings are stored as JSON arrays of floats to maintain compatibility
    with standard SQLite without requiring vector extensions.
    """
    __tablename__ = "patient_rag_chunks"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, index=True, nullable=False)
    
    # Optional link to the source document if this chunk came from a document
    source_document_id = Column(String, ForeignKey("documents.document_id", ondelete="SET NULL"), nullable=True)
    
    # The actual text content that was embedded
    content = Column(Text, nullable=False)
    
    # The vector embedding, serialized as a JSON list of floats
    embedding = Column(JSON, nullable=False)
    
    # Metadata for citation (e.g. page number, section heading, field name)
    metadata_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
