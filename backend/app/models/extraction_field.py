import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Float, ForeignKey, JSON
from app.database import Base
from app.models.document import Document  # Ensure Document model is registered in Base.metadata


class ExtractionField(Base):
    __tablename__ = "extraction_fields"

    field_id = Column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True
    )
    document_id = Column(
        String(36),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    field_name = Column(String(100), nullable=False)
    raw_value = Column(String(500), nullable=True)
    confidence = Column(Float, nullable=True)
    status = Column(String(50), nullable=True)
    bounding_box = Column(JSON, nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
