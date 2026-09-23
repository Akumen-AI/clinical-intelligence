import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship

from app.database import Base


def default_expiration():
    """Conversations expire and can be cleaned up after 30 days of inactivity."""
    return datetime.utcnow() + timedelta(days=30)


class RAGConversation(Base):
    """
    Stores conversational history for patient RAG QA sessions to allow
    follow-up context.
    """
    __tablename__ = "rag_conversations"

    id = Column(String, primary_key=True, index=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, default=default_expiration)
    
    # Relationship to individual messages
    messages = relationship(
        "RAGMessage",
        back_populates="conversation",
        order_by="RAGMessage.created_at",
        cascade="all, delete-orphan"
    )

    @property
    def turns(self):
        """
        Backwards compatibility property to return turns as a list of dicts.
        """
        return [{"role": m.role, "content": m.content} for m in self.messages]

