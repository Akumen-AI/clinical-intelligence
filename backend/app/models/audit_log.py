import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, TypeDecorator
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

class GUID(TypeDecorator):
    """Platform-independent GUID type."""
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))

class AuditLogEntry(Base):
    __tablename__ = "audit_log_entries"

    log_id: Mapped[uuid.UUID] = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(GUID, nullable=False, index=True)
    action_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    target_entity: Mapped[str] = mapped_column(String, nullable=False)
    patient_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    rationale: Mapped[str | None] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
