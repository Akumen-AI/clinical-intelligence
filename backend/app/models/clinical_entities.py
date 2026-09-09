import uuid
from sqlalchemy import Column, String, Float, ForeignKey, Index

from app.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Medication(Base):
    __tablename__ = "medications"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String(36), ForeignKey("patients.patient_id"), nullable=False, index=True)
    source_field_id = Column(String(36), ForeignKey("extracted_fields.field_id"), nullable=False, index=True)
    raw_text = Column(String(500), nullable=False)
    rxnorm_code = Column(String(100), nullable=True)
    mapping_source = Column(String(100), nullable=True)
    mapping_version = Column(String(50), nullable=True)
    status = Column(String(20), nullable=True, default="active")
    discontinued_reason = Column(String(500), nullable=True)
    discontinued_date = Column(String(100), nullable=True)
    started_date = Column(String(100), nullable=True)


class Diagnosis(Base):
    __tablename__ = "diagnoses"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String(36), ForeignKey("patients.patient_id"), nullable=False, index=True)
    source_field_id = Column(String(36), ForeignKey("extracted_fields.field_id"), nullable=False, index=True)
    raw_text = Column(String(500), nullable=False)
    icd10_code = Column(String(100), nullable=True)
    mapping_source = Column(String(100), nullable=True)
    mapping_version = Column(String(50), nullable=True)


class Allergy(Base):
    __tablename__ = "allergies"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String(36), ForeignKey("patients.patient_id"), nullable=False, index=True)
    source_field_id = Column(String(36), ForeignKey("extracted_fields.field_id"), nullable=True, index=True)
    raw_text = Column(String(500), nullable=False)
    allergen = Column(String(255), nullable=False)
    reaction = Column(String(500), nullable=True)
    severity = Column(String(20), nullable=True)


class LabResult(Base):
    __tablename__ = "lab_results"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String(36), ForeignKey("patients.patient_id"), nullable=False, index=True)
    source_field_id = Column(String(36), ForeignKey("extracted_fields.field_id"), nullable=False, index=True)
    raw_text = Column(String(500), nullable=False)
    loinc_code = Column(String(100), nullable=True)
    test_name = Column(String(255), nullable=True)
    value_text = Column(String(255), nullable=True)
    value_numeric = Column(Float, nullable=True)
    unit = Column(String(50), nullable=True)
    reference_range = Column(String(100), nullable=True)
    flag = Column(String(20), nullable=True)
    recorded_at = Column(String(100), nullable=True)


class Vital(Base):
    __tablename__ = "vitals"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String(36), ForeignKey("patients.patient_id"), nullable=False, index=True)
    source_field_id = Column(String(36), ForeignKey("extracted_fields.field_id"), nullable=False, index=True)
    raw_text = Column(String(500), nullable=False)
    type = Column(String(100), nullable=True)
    value = Column(String(255), nullable=True)
    recorded_at = Column(String(100), nullable=True)


class Procedure(Base):
    __tablename__ = "procedures"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    patient_id = Column(String(36), ForeignKey("patients.patient_id"), nullable=False, index=True)
    source_field_id = Column(String(36), ForeignKey("extracted_fields.field_id"), nullable=False, index=True)
    raw_text = Column(String(500), nullable=False)
    code = Column(String(100), nullable=True)
    description = Column(String(500), nullable=True)
    date = Column(String(100), nullable=True)
