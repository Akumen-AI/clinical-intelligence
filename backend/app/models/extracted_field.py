import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    JSON,
    String,
)
from sqlalchemy.orm import synonym
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    __table_args__ = (
        CheckConstraint(
            "confidence_score >= 0.0 AND confidence_score <= 1.0",
            name="ck_extracted_fields_confidence_range",
        ),
        Index(
            "ix_extracted_fields_doc_confidence",
            "document_id",
            "confidence_score",
        ),
    )

    field_id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    id = synonym("field_id")
    document_id = Column(
        String(36),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name = Column(String(100), nullable=False, index=True)
    raw_value = Column(JSON, nullable=True)
    confidence_score = Column(Float, default=0.0, nullable=False)
    bounding_box = Column(JSON, nullable=True)
    # verification_status valid values:
    #   "extracted"  — field was extracted normally by OCR or LLM
    #   "verified"   — field was manually verified/corrected by a human reviewer
    #   "illegible"  — field could not be read from handwritten content with
    #                  reasonable confidence; requires manual entry.
    #                  When set, confidence_score will be 0.0 and the parent
    #                  Document.needs_manual_review will be True.
    verification_status = Column(String(50), default="extracted", nullable=False)
    verified_value = Column(JSON, nullable=True)
    reviewer_id = Column(String(36), nullable=True)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
