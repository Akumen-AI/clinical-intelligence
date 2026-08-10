"""
Clinical child record models — visits, medications, diagnoses, vitals, labs, procedures.

Each table:
  - Uses String(36) UUID primary keys (matching the documents / patients pattern).
  - Has a patient_id FK → patients.id (String(36), nullable=False).
  - Has an optional visit_id FK → visits.id (String(36), nullable=True).
  - Has an optional source_document_id FK → documents.document_id (String(36),
    nullable=True) — populated when a record was extracted from a document via
    the extraction pipeline.  Manual entries leave this NULL.

Auth: no auth applied on CRUD routes — consistent with all existing routes.
RBAC retrofit is tracked in Epic 9.

NOTE: wiring the extraction pipeline to write into these tables is a
follow-up task (Epic 9 / extraction pipeline integration).  The existing
canonical_record_service.upsert_field continues to write to extracted_fields
unchanged.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Date, DateTime, Text, ForeignKey
from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Visit
# ---------------------------------------------------------------------------

class Visit(Base):
    """One patient encounter / clinical visit."""

    __tablename__ = "visits"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(
        String(36),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    visit_date = Column(Date, nullable=True)
    visit_type = Column(String(100), nullable=True)   # e.g. "outpatient", "inpatient", "ER"
    notes = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Medication
# ---------------------------------------------------------------------------

class Medication(Base):
    """Medication prescribed or administered during a visit (or standalone)."""

    __tablename__ = "medications"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(
        String(36),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    visit_id = Column(
        String(36),
        ForeignKey("visits.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    name = Column(String(255), nullable=False)
    dosage = Column(String(100), nullable=True)        # e.g. "500mg"
    frequency = Column(String(100), nullable=True)     # e.g. "twice daily"
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)
    status = Column(String(50), nullable=True)         # e.g. "active", "discontinued"
    source_document_id = Column(
        String(36),
        ForeignKey("documents.document_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Diagnosis
# ---------------------------------------------------------------------------

class Diagnosis(Base):
    """Clinical diagnosis attached to a patient (optionally to a visit)."""

    __tablename__ = "diagnoses"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(
        String(36),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    visit_id = Column(
        String(36),
        ForeignKey("visits.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    description = Column(Text, nullable=False)         # Free-text or ICD code + description
    diagnosis_date = Column(Date, nullable=True)
    source_document_id = Column(
        String(36),
        ForeignKey("documents.document_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Vital
# ---------------------------------------------------------------------------

class Vital(Base):
    """Single vital-sign measurement."""

    __tablename__ = "vitals"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(
        String(36),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    visit_id = Column(
        String(36),
        ForeignKey("visits.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    vital_type = Column(String(100), nullable=False)   # e.g. "blood_pressure", "heart_rate"
    value = Column(String(100), nullable=False)        # Stored as string to handle ranges ("120/80")
    unit = Column(String(50), nullable=True)           # e.g. "mmHg", "bpm"
    recorded_at = Column(DateTime(timezone=True), nullable=True)
    source_document_id = Column(
        String(36),
        ForeignKey("documents.document_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Lab
# ---------------------------------------------------------------------------

class Lab(Base):
    """Laboratory test result."""

    __tablename__ = "labs"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(
        String(36),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    visit_id = Column(
        String(36),
        ForeignKey("visits.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    test_name = Column(String(255), nullable=False)    # e.g. "HbA1c", "Complete Blood Count"
    result_value = Column(String(100), nullable=True)  # String to handle text results ("Positive")
    unit = Column(String(50), nullable=True)           # e.g. "%", "mg/dL"
    reference_range = Column(String(100), nullable=True)  # e.g. "4.0-5.6"
    test_date = Column(Date, nullable=True)
    source_document_id = Column(
        String(36),
        ForeignKey("documents.document_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


# ---------------------------------------------------------------------------
# Procedure
# ---------------------------------------------------------------------------

class Procedure(Base):
    """Clinical procedure performed on a patient."""

    __tablename__ = "procedures"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(
        String(36),
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    visit_id = Column(
        String(36),
        ForeignKey("visits.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    procedure_name = Column(String(255), nullable=False)
    procedure_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    source_document_id = Column(
        String(36),
        ForeignKey("documents.document_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
