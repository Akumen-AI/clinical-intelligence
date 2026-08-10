import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Date, DateTime
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Patient(Base):
    """
    Canonical patient identity record.

    ``id`` uses the same String(36) UUID format as ``documents.patient_id``
    so that a foreign-key relationship can be established between the two
    tables without any type conversion.

    Populated by: manual API entry (POST /api/v1/patients).
    Auth: no auth applied — consistent with all other existing routes.
    RBAC retrofit is tracked in Epic 9.
    """

    __tablename__ = "patients"

    # Primary key — String(36) UUID, matches documents.patient_id type exactly
    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)

    # Demographic fields
    name = Column(String(255), nullable=False)
    dob = Column(Date, nullable=True)          # Date of birth (YYYY-MM-DD)
    gender = Column(String(50), nullable=True)  # e.g. "male", "female", "other"

    # Medical Record Number — nullable; uniqueness not enforced here to avoid
    # blocking partial data.  A UNIQUE constraint can be added via migration
    # once data-hygiene guarantees it.
    mrn = Column(String(50), nullable=True, index=True)

    # Audit timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
