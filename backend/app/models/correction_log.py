import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    UUID, String, Text, Float, Boolean, DateTime,
    CheckConstraint, ForeignKey, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class CorrectionLog(Base):
    __tablename__ = "correction_logs"
    __table_args__ = (
        CheckConstraint("action IN ('accept','edit','reject')", name="ck_correction_action"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    extracted_field_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("extracted_fields.field_id", ondelete="CASCADE"), nullable=False)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("documents.document_id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(10), nullable=False)
    before_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    field_name: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reviewer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    reviewer_role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    retraining_exported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    export_batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships (back-populate if those models exist)
    # extracted_field = relationship("ExtractedField", back_populates="correction_logs")
    # reviewer = relationship("User", back_populates="correction_logs")
