import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, JSON
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    field_id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    document_id = Column(
        String(36),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name = Column(String(100), nullable=False, index=True)
    raw_value = Column(JSON, nullable=True)
    confidence_score = Column(Float, default=1.0, nullable=False)
    bounding_box = Column(JSON, nullable=True)
    verification_status = Column(String(50), default="extracted", nullable=False)
    verified_value = Column(JSON, nullable=True)
    reviewer_id = Column(String(36), nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
