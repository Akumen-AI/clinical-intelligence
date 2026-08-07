import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    String,
    Text,
)
from app.database import Base


class ReviewStatus(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


def generate_uuid() -> str:
    return str(uuid.uuid4())


class PendingReview(Base):
    __tablename__ = "pending_review"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    document_id = Column(
        String(36),
        ForeignKey("documents.document_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    field_name = Column(String(100), nullable=False, index=True)
    extracted_value = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=False)
    status = Column(
        SQLEnum(ReviewStatus, name="reviewstatus_enum", values_callable=lambda x: [e.value for e in x]),
        default=ReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    reviewer_id = Column(String(36), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SystemConfig(Base):
    __tablename__ = "system_config"

    key = Column(String(50), primary_key=True, index=True)
    value = Column(String(255), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
