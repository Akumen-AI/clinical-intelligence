import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from app.models.audit_log import GUID


class PatientDuplicateFlag(Base):
    __tablename__ = "patient_duplicate_flags"

    id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    patient_a_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False)
    patient_b_id: Mapped[uuid.UUID] = mapped_column(GUID, ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    match_reasons: Mapped[list[str]] = mapped_column(ARRAY(String).with_variant(JSON, "sqlite"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending", index=True)
    flagged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("users.id"), nullable=True)
    merged_into_id: Mapped[uuid.UUID | None] = mapped_column(GUID, ForeignKey("patients.patient_id"), nullable=True)
