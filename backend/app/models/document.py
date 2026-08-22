from datetime import datetime, timezone
import enum
from sqlalchemy import Column, String, DateTime, Integer, Float, Boolean, ForeignKey
from sqlalchemy.orm import synonym
from app.database import Base

class DocumentStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    NEW = "new"
    PREPROCESSING = "PREPROCESSING"
    DETECTING_LAYOUT = "detecting_layout"
    CLASSIFYING = "classifying"
    EXTRACTING = "extracting"
    PREPROCESSED = "preprocessed"
    CLASSIFIED = "classified"
    EXTRACTED = "extracted"
    UNLINKED = "unlinked"
    PENDING_REVIEW = "pending_review"
    COMMITTED = "committed"
    FAILED = "failed"

class Document(Base):
    __tablename__ = "documents"

    document_id = Column(String(36), primary_key=True, index=True)
    id = synonym("document_id")
    patient_id = Column(String(36), ForeignKey("patients.patient_id"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    raw_uri = Column(String(500), nullable=False)
    filetype = Column(String(50), nullable=False)
    status = Column(String(50), default=DocumentStatus.QUEUED.value, nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_uri = Column(String(500), nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    document_type = Column(String(100), nullable=True)
    classification_confidence = Column(Float, nullable=True)
    extraction_confidence = Column(Float, nullable=True)
    needs_manual_review = Column(Boolean, default=False, nullable=False)
    rejection_reason = Column(String(500), nullable=True)

