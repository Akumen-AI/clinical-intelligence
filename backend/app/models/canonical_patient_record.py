import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Index, JSON, String, UniqueConstraint

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class CanonicalPatientRecord(Base):
    """Verified field values admitted to the canonical patient record."""

    __tablename__ = "canonical_patient_records"
    __table_args__ = (
        UniqueConstraint("document_id", "field_name", name="uq_canonical_document_field"),
        Index("ix_canonical_patient_records_document", "document_id"),
    )

    record_id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    value = Column(JSON, nullable=True)
    source_field_id = Column(String(36), nullable=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
