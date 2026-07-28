from datetime import datetime, timezone
import enum
from sqlalchemy import Column, String, DateTime, Integer
from app.database import Base

class DocumentStatus(str, enum.Enum):
    NEW = "new"
    PREPROCESSED = "preprocessed"
    EXTRACTED = "extracted"
    PENDING_REVIEW = "pending_review"
    COMMITTED = "committed"
    FAILED = "failed"

class Document(Base):
    __tablename__ = "documents"

    document_id = Column(String(36), primary_key=True, index=True)
    patient_id = Column(String(36), nullable=True)
    filename = Column(String(255), nullable=False)
    raw_uri = Column(String(500), nullable=False)
    filetype = Column(String(50), nullable=False)
    status = Column(String(50), default=DocumentStatus.NEW.value, nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_uri = Column(String(500), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    doc_type = Column(String(100), nullable=True)
    rejection_reason = Column(String(500), nullable=True)
