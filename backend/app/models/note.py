import uuid
from datetime import datetime
from sqlalchemy import String, Text, ForeignKey, TypeDecorator, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class GUID(TypeDecorator):
    """Platform-independent GUID type.
    Uses String(36) on SQLite, UUID on Postgres.
    """
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


class Note(Base):
    __tablename__ = "notes"

    id:             Mapped[uuid.UUID]  = mapped_column(GUID, primary_key=True, default=uuid.uuid4)
    patient_id:     Mapped[uuid.UUID]  = mapped_column(GUID, ForeignKey("patients.patient_id", ondelete="CASCADE"), nullable=False)
    author_id:      Mapped[uuid.UUID]  = mapped_column(GUID, ForeignKey("users.id"), nullable=False)
    author_role:    Mapped[str]        = mapped_column(String(64), nullable=False)
    complaint_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content:        Mapped[str]        = mapped_column(Text, nullable=False)
    created_at:     Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at:     Mapped[datetime]   = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
