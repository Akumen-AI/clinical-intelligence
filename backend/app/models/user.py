import enum
import uuid
from datetime import datetime, timezone
from sqlalchemy import UUID, String, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class UserRole(str, enum.Enum):
    DOCTOR = "doctor"
    NURSE = "nurse"
    HOSPITAL_ADMIN = "hospital_admin"
    DEPARTMENT_HEAD = "department_head"
    IT = "it"
    COMPLIANCE = "compliance"

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, default="reviewer@clinic.org")
    role: Mapped[UserRole] = mapped_column(SAEnum(UserRole), nullable=False, default=UserRole.NURSE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
