import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON

from app.database import Base


class RAGConversation(Base):
    """
    Stores conversational history for patient RAG QA sessions to allow
    follow-up context.
    """
    __tablename__ = "rag_conversations"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    
    # Store turns as a JSON array of dicts: [{"role": "user", "content": "..."}]
    turns = Column(JSON, default=list, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
