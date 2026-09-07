import uuid
from datetime import datetime, timezone
from sqlalchemy import UUID, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class AuditLogEntry(Base):
    __tablename__ = "audit_log_entries"

    log_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target_entity: Mapped[str] = mapped_column(String, nullable=False)
    patient_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    rationale: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
