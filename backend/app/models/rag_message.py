import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.database import Base


class RAGMessage(Base):
    """
    Stores individual messages within a RAG conversation.
    Append-only model to prevent concurrent modifications from wiping history.
    """
    __tablename__ = "rag_messages"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("rag_conversations.id", ondelete="CASCADE"), index=True, nullable=False)
    
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(String, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to conversation
    conversation = relationship("RAGConversation", back_populates="messages")
