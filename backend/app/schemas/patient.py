"""
Pydantic schemas for the canonical patient record API.

Naming conventions match the existing schema files in this package
(ConfigDict(from_attributes=True), optional fields use Optional[X] = None,
create/update/response triptych per entity).

Auth: no auth applied on any route — consistent with all existing routes.
RBAC retrofit is tracked in Epic 9.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ─────────────────────────────────────────────────────────────────────────────
# Patient
# ─────────────────────────────────────────────────────────────────────────────

class PatientCreate(BaseModel):
    """Payload for POST /api/v1/patients."""

    name: str = Field(..., description="Full patient name")
    dob: Optional[date] = Field(None, description="Date of birth (YYYY-MM-DD)")
    gender: Optional[str] = Field(None, description="Gender (e.g. male / female / other)")
    mrn: Optional[str] = Field(None, description="Medical Record Number")


class PatientUpdate(BaseModel):
    """Payload for PUT /api/v1/patients/{patient_id}. All fields optional."""

    name: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    mrn: Optional[str] = None


class PatientBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    dob: Optional[date] = None
    gender: Optional[str] = None
    mrn: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PatientResponse(PatientBase):
    """
    Full canonical record — patient demographics + all nested child lists.
    Returned by GET /api/v1/patients/{patient_id}.
    """

    visits: List[VisitResponse] = []
    medications: List[MedicationResponse] = []
    diagnoses: List[DiagnosisResponse] = []
    vitals: List[VitalResponse] = []
    labs: List[LabResponse] = []
    procedures: List[ProcedureResponse] = []


# ─────────────────────────────────────────────────────────────────────────────
# Visit
# ─────────────────────────────────────────────────────────────────────────────

class VisitCreate(BaseModel):
    """Payload for POST /api/v1/patients/{patient_id}/visits."""

    visit_date: Optional[date] = None
    visit_type: Optional[str] = None
    notes: Optional[str] = None


class VisitUpdate(BaseModel):
    """Payload for PUT /api/v1/patients/{patient_id}/visits/{visit_id}."""

    visit_date: Optional[date] = None
    visit_type: Optional[str] = None
    notes: Optional[str] = None


class VisitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    visit_date: Optional[date] = None
    visit_type: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Medication
# ─────────────────────────────────────────────────────────────────────────────

class MedicationCreate(BaseModel):
    """Payload for POST /api/v1/patients/{patient_id}/medications."""

    name: str
    visit_id: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    source_document_id: Optional[str] = None


class MedicationUpdate(BaseModel):
    """Payload for PUT /api/v1/patients/{patient_id}/medications/{medication_id}."""

    name: Optional[str] = None
    visit_id: Optional[str] = None
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    source_document_id: Optional[str] = None


class MedicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    visit_id: Optional[str] = None
    name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: Optional[str] = None
    source_document_id: Optional[str] = None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Diagnosis
# ─────────────────────────────────────────────────────────────────────────────

class DiagnosisCreate(BaseModel):
    """Payload for POST /api/v1/patients/{patient_id}/diagnoses."""

    description: str
    visit_id: Optional[str] = None
    diagnosis_date: Optional[date] = None
    source_document_id: Optional[str] = None


class DiagnosisUpdate(BaseModel):
    """Payload for PUT /api/v1/patients/{patient_id}/diagnoses/{diagnosis_id}."""

    description: Optional[str] = None
    visit_id: Optional[str] = None
    diagnosis_date: Optional[date] = None
    source_document_id: Optional[str] = None


class DiagnosisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    visit_id: Optional[str] = None
    description: str
    diagnosis_date: Optional[date] = None
    source_document_id: Optional[str] = None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Vital
# ─────────────────────────────────────────────────────────────────────────────

class VitalCreate(BaseModel):
    """Payload for POST /api/v1/patients/{patient_id}/vitals."""

    vital_type: str
    value: str
    visit_id: Optional[str] = None
    unit: Optional[str] = None
    recorded_at: Optional[datetime] = None
    source_document_id: Optional[str] = None


class VitalUpdate(BaseModel):
    """Payload for PUT /api/v1/patients/{patient_id}/vitals/{vital_id}."""

    vital_type: Optional[str] = None
    value: Optional[str] = None
    visit_id: Optional[str] = None
    unit: Optional[str] = None
    recorded_at: Optional[datetime] = None
    source_document_id: Optional[str] = None


class VitalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    visit_id: Optional[str] = None
    vital_type: str
    value: str
    unit: Optional[str] = None
    recorded_at: Optional[datetime] = None
    source_document_id: Optional[str] = None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Lab
# ─────────────────────────────────────────────────────────────────────────────

class LabCreate(BaseModel):
    """Payload for POST /api/v1/patients/{patient_id}/labs."""

    test_name: str
    visit_id: Optional[str] = None
    result_value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    test_date: Optional[date] = None
    source_document_id: Optional[str] = None


class LabUpdate(BaseModel):
    """Payload for PUT /api/v1/patients/{patient_id}/labs/{lab_id}."""

    test_name: Optional[str] = None
    visit_id: Optional[str] = None
    result_value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    test_date: Optional[date] = None
    source_document_id: Optional[str] = None


class LabResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    visit_id: Optional[str] = None
    test_name: str
    result_value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    test_date: Optional[date] = None
    source_document_id: Optional[str] = None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Procedure
# ─────────────────────────────────────────────────────────────────────────────

class ProcedureCreate(BaseModel):
    """Payload for POST /api/v1/patients/{patient_id}/procedures."""

    procedure_name: str
    visit_id: Optional[str] = None
    procedure_date: Optional[date] = None
    notes: Optional[str] = None
    source_document_id: Optional[str] = None


class ProcedureUpdate(BaseModel):
    """Payload for PUT /api/v1/patients/{patient_id}/procedures/{procedure_id}."""

    procedure_name: Optional[str] = None
    visit_id: Optional[str] = None
    procedure_date: Optional[date] = None
    notes: Optional[str] = None
    source_document_id: Optional[str] = None


class ProcedureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    visit_id: Optional[str] = None
    procedure_name: str
    procedure_date: Optional[date] = None
    notes: Optional[str] = None
    source_document_id: Optional[str] = None
    created_at: datetime


# Forward-ref resolution (PatientResponse references child Response classes
# defined after it in this module; update_forward_refs resolves that)
PatientResponse.model_rebuild()
