import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Index

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Visit(Base):
    __tablename__ = "visits"

    visit_id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String(36), ForeignKey("patients.patient_id"), nullable=False, index=True)
    visit_date = Column(DateTime, nullable=True)
    department = Column(String(255), nullable=True)
