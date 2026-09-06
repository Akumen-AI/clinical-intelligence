import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Index

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_number = Column(String(50), nullable=True, unique=True, index=True)
    mrn = Column(String(50), nullable=True, index=True)
    name = Column(String(255), nullable=True)
    dob = Column(String(50), nullable=True)
    sex = Column(String(50), nullable=True)
    duplicate_of = Column(String(36), ForeignKey("patients.patient_id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    @property
    def id(self):
        return self.patient_id

