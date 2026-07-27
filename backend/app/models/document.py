from datetime import datetime, timezone
import enum
from sqlalchemy import Column, String, DateTime
from app.database import Base

class DocumentStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    PREPROCESSING = "PREPROCESSING"
    OCR_RUNNING = "OCR_RUNNING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"

class Document(Base):
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    filetype = Column(String(50), nullable=False)
    status = Column(String(50), default=DocumentStatus.QUEUED.value, nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_path = Column(String(500), nullable=True)
    classification = Column(String(100), nullable=True)
