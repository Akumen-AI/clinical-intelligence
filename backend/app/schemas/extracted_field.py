from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class PatientIdentifierSchema(BaseModel):
    patient_id: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None
    gender: Optional[str] = None


class PhysicianSchema(BaseModel):
    name: Optional[str] = None
    npi_or_license: Optional[str] = None
    department: Optional[str] = None


class VitalsSchema(BaseModel):
    blood_pressure: Optional[str] = None
    heart_rate: Optional[str] = None
    respiratory_rate: Optional[str] = None
    temperature: Optional[str] = None
    spo2: Optional[str] = None
    weight: Optional[str] = None
    height: Optional[str] = None
    bmi: Optional[str] = None


class DiagnosisItemSchema(BaseModel):
    condition_name: str
    icd10_code: Optional[str] = None
    notes: Optional[str] = None


class MedicationItemSchema(BaseModel):
    medication_name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    duration: Optional[str] = None
    instructions: Optional[str] = None


class LabResultItemSchema(BaseModel):
    test_name: str
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    flag: Optional[str] = None  # e.g. Normal, High, Low, Abnormal


class AllergyItemSchema(BaseModel):
    allergen: str
    reaction: Optional[str] = None
    severity: Optional[str] = None


class ClinicalFieldsSchema(BaseModel):
    """
    Standard structured schema for all extracted key clinical fields.
    Every key is explicitly defined so missing fields serialize to `null`,
    satisfying FR-07 Acceptance Criterion 3.
    """
    patient_identifier: Optional[PatientIdentifierSchema] = None
    document_date: Optional[str] = None
    ordering_physician: Optional[PhysicianSchema] = None
    vitals: Optional[VitalsSchema] = None
    diagnosis: Optional[List[DiagnosisItemSchema]] = None
    medications: Optional[List[MedicationItemSchema]] = None
    lab_results: Optional[List[LabResultItemSchema]] = None
    symptoms: Optional[List[str]] = None
    procedures: Optional[List[str]] = None
    allergies: Optional[List[AllergyItemSchema]] = None


class ExtractedFieldRecordSchema(BaseModel):
    field_id: str
    document_id: str
    field_name: str
    raw_value: Optional[Any] = None
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    bounding_box: Optional[Any] = None
    verification_status: str = "extracted"
    verified_value: Optional[Any] = None
    reviewer_id: Optional[str] = None
    created_at: datetime


class DocumentFieldsResponseSchema(BaseModel):
    document_id: str
    document_type: Optional[str] = None
    fields: ClinicalFieldsSchema
    field_records: List[ExtractedFieldRecordSchema]
