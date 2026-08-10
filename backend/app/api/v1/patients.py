"""
Patients CRUD API — /api/v1/patients

Endpoints:
  POST   /api/v1/patients                                   — create patient
  GET    /api/v1/patients/{patient_id}                      — full canonical record
  PUT    /api/v1/patients/{patient_id}                      — update patient demographics

  POST   /api/v1/patients/{patient_id}/visits               — add visit
  PUT    /api/v1/patients/{patient_id}/visits/{visit_id}    — update visit

  POST   /api/v1/patients/{patient_id}/medications          — add medication
  PUT    /api/v1/patients/{patient_id}/medications/{medication_id}

  POST   /api/v1/patients/{patient_id}/diagnoses            — add diagnosis
  PUT    /api/v1/patients/{patient_id}/diagnoses/{diagnosis_id}

  POST   /api/v1/patients/{patient_id}/vitals               — add vital sign
  PUT    /api/v1/patients/{patient_id}/vitals/{vital_id}

  POST   /api/v1/patients/{patient_id}/labs                 — add lab result
  PUT    /api/v1/patients/{patient_id}/labs/{lab_id}

  POST   /api/v1/patients/{patient_id}/procedures           — add procedure
  PUT    /api/v1/patients/{patient_id}/procedures/{procedure_id}

# ── Auth note ─────────────────────────────────────────────────────────────────
# No authentication dependency is applied here.  All existing routes in this
# project (upload, layout, fields, review) are also unauthenticated.
# Retrofitting RBAC to these routes is tracked in Epic 9.
# ─────────────────────────────────────────────────────────────────────────────
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.patient import Patient
from app.models.clinical_record import (
    Diagnosis,
    Lab,
    Medication,
    Procedure,
    Vital,
    Visit,
)
from app.schemas.patient import (
    DiagnosisCreate,
    DiagnosisResponse,
    DiagnosisUpdate,
    LabCreate,
    LabResponse,
    LabUpdate,
    MedicationCreate,
    MedicationResponse,
    MedicationUpdate,
    PatientCreate,
    PatientResponse,
    PatientUpdate,
    ProcedureCreate,
    ProcedureResponse,
    ProcedureUpdate,
    VitalCreate,
    VitalResponse,
    VitalUpdate,
    VisitCreate,
    VisitResponse,
    VisitUpdate,
)

logger = logging.getLogger("app.api.v1.patients")

router = APIRouter(
    prefix="/patients",
    tags=["Canonical Patient Record (Epic 8)"],
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _generate_uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _get_patient_or_404(patient_id: str, db: Session) -> Patient:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient '{patient_id}' not found.",
        )
    return patient


def _build_patient_response(patient: Patient, db: Session) -> PatientResponse:
    """Assemble the full canonical record for a patient."""
    visits = db.query(Visit).filter(Visit.patient_id == patient.id).all()
    medications = db.query(Medication).filter(Medication.patient_id == patient.id).all()
    diagnoses = db.query(Diagnosis).filter(Diagnosis.patient_id == patient.id).all()
    vitals = db.query(Vital).filter(Vital.patient_id == patient.id).all()
    labs = db.query(Lab).filter(Lab.patient_id == patient.id).all()
    procedures = db.query(Procedure).filter(Procedure.patient_id == patient.id).all()

    return PatientResponse(
        id=patient.id,
        name=patient.name,
        dob=patient.dob,
        gender=patient.gender,
        mrn=patient.mrn,
        created_at=patient.created_at,
        updated_at=patient.updated_at,
        visits=[VisitResponse.model_validate(v) for v in visits],
        medications=[MedicationResponse.model_validate(m) for m in medications],
        diagnoses=[DiagnosisResponse.model_validate(d) for d in diagnoses],
        vitals=[VitalResponse.model_validate(v) for v in vitals],
        labs=[LabResponse.model_validate(l) for l in labs],
        procedures=[ProcedureResponse.model_validate(p) for p in procedures],
    )


def _set_fields(obj: Any, payload: Any) -> None:
    """Apply non-None fields from a Pydantic update payload onto an ORM object."""
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)


# ── Patient endpoints ─────────────────────────────────────────────────────────

@router.post(
    "/",
    response_model=PatientResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new patient",
)
def create_patient(
    payload: PatientCreate,
    db: Session = Depends(get_db),
):
    """
    POST /api/v1/patients

    Creates a canonical patient record.  Returns the full record including
    empty child lists (visits, medications, etc.).
    """
    patient = Patient(
        id=_generate_uuid(),
        name=payload.name,
        dob=payload.dob,
        gender=payload.gender,
        mrn=payload.mrn,
        created_at=_now(),
        updated_at=_now(),
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    logger.info("[Patients] Created patient %s (name=%s)", patient.id, patient.name)
    return _build_patient_response(patient, db)


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Get full canonical patient record",
)
def get_patient(
    patient_id: str,
    db: Session = Depends(get_db),
):
    """
    GET /api/v1/patients/{patient_id}

    Returns the full canonical patient record including all nested child
    entities: visits, medications, diagnoses, vitals, labs, and procedures.
    """
    patient = _get_patient_or_404(patient_id, db)
    return _build_patient_response(patient, db)


@router.put(
    "/{patient_id}",
    response_model=PatientResponse,
    status_code=status.HTTP_200_OK,
    summary="Update patient demographics",
)
def update_patient(
    patient_id: str,
    payload: PatientUpdate,
    db: Session = Depends(get_db),
):
    """
    PUT /api/v1/patients/{patient_id}

    Updates one or more patient demographic fields.  Only supplied fields are
    modified (partial update semantics).
    """
    patient = _get_patient_or_404(patient_id, db)
    _set_fields(patient, payload)
    patient.updated_at = _now()
    db.commit()
    db.refresh(patient)
    logger.info("[Patients] Updated patient %s", patient.id)
    return _build_patient_response(patient, db)


# ── Visit endpoints ───────────────────────────────────────────────────────────

@router.post(
    "/{patient_id}/visits",
    response_model=VisitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a visit to a patient record",
)
def create_visit(
    patient_id: str,
    payload: VisitCreate,
    db: Session = Depends(get_db),
):
    """POST /api/v1/patients/{patient_id}/visits"""
    _get_patient_or_404(patient_id, db)
    visit = Visit(
        id=_generate_uuid(),
        patient_id=patient_id,
        visit_date=payload.visit_date,
        visit_type=payload.visit_type,
        notes=payload.notes,
        created_at=_now(),
    )
    db.add(visit)
    db.commit()
    db.refresh(visit)
    return VisitResponse.model_validate(visit)


@router.put(
    "/{patient_id}/visits/{visit_id}",
    response_model=VisitResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a visit record",
)
def update_visit(
    patient_id: str,
    visit_id: str,
    payload: VisitUpdate,
    db: Session = Depends(get_db),
):
    """PUT /api/v1/patients/{patient_id}/visits/{visit_id}"""
    _get_patient_or_404(patient_id, db)
    visit = db.query(Visit).filter(Visit.id == visit_id, Visit.patient_id == patient_id).first()
    if not visit:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Visit '{visit_id}' not found.")
    _set_fields(visit, payload)
    db.commit()
    db.refresh(visit)
    return VisitResponse.model_validate(visit)


# ── Medication endpoints ──────────────────────────────────────────────────────

@router.post(
    "/{patient_id}/medications",
    response_model=MedicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a medication to a patient record",
)
def create_medication(
    patient_id: str,
    payload: MedicationCreate,
    db: Session = Depends(get_db),
):
    """POST /api/v1/patients/{patient_id}/medications"""
    _get_patient_or_404(patient_id, db)
    med = Medication(
        id=_generate_uuid(),
        patient_id=patient_id,
        visit_id=payload.visit_id,
        name=payload.name,
        dosage=payload.dosage,
        frequency=payload.frequency,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
        source_document_id=payload.source_document_id,
        created_at=_now(),
    )
    db.add(med)
    db.commit()
    db.refresh(med)
    return MedicationResponse.model_validate(med)


@router.put(
    "/{patient_id}/medications/{medication_id}",
    response_model=MedicationResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a medication record",
)
def update_medication(
    patient_id: str,
    medication_id: str,
    payload: MedicationUpdate,
    db: Session = Depends(get_db),
):
    """PUT /api/v1/patients/{patient_id}/medications/{medication_id}"""
    _get_patient_or_404(patient_id, db)
    med = db.query(Medication).filter(
        Medication.id == medication_id, Medication.patient_id == patient_id
    ).first()
    if not med:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Medication '{medication_id}' not found.")
    _set_fields(med, payload)
    db.commit()
    db.refresh(med)
    return MedicationResponse.model_validate(med)


# ── Diagnosis endpoints ───────────────────────────────────────────────────────

@router.post(
    "/{patient_id}/diagnoses",
    response_model=DiagnosisResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a diagnosis to a patient record",
)
def create_diagnosis(
    patient_id: str,
    payload: DiagnosisCreate,
    db: Session = Depends(get_db),
):
    """POST /api/v1/patients/{patient_id}/diagnoses"""
    _get_patient_or_404(patient_id, db)
    diag = Diagnosis(
        id=_generate_uuid(),
        patient_id=patient_id,
        visit_id=payload.visit_id,
        description=payload.description,
        diagnosis_date=payload.diagnosis_date,
        source_document_id=payload.source_document_id,
        created_at=_now(),
    )
    db.add(diag)
    db.commit()
    db.refresh(diag)
    return DiagnosisResponse.model_validate(diag)


@router.put(
    "/{patient_id}/diagnoses/{diagnosis_id}",
    response_model=DiagnosisResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a diagnosis record",
)
def update_diagnosis(
    patient_id: str,
    diagnosis_id: str,
    payload: DiagnosisUpdate,
    db: Session = Depends(get_db),
):
    """PUT /api/v1/patients/{patient_id}/diagnoses/{diagnosis_id}"""
    _get_patient_or_404(patient_id, db)
    diag = db.query(Diagnosis).filter(
        Diagnosis.id == diagnosis_id, Diagnosis.patient_id == patient_id
    ).first()
    if not diag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Diagnosis '{diagnosis_id}' not found.")
    _set_fields(diag, payload)
    db.commit()
    db.refresh(diag)
    return DiagnosisResponse.model_validate(diag)


# ── Vital endpoints ───────────────────────────────────────────────────────────

@router.post(
    "/{patient_id}/vitals",
    response_model=VitalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a vital sign to a patient record",
)
def create_vital(
    patient_id: str,
    payload: VitalCreate,
    db: Session = Depends(get_db),
):
    """POST /api/v1/patients/{patient_id}/vitals"""
    _get_patient_or_404(patient_id, db)
    vital = Vital(
        id=_generate_uuid(),
        patient_id=patient_id,
        visit_id=payload.visit_id,
        vital_type=payload.vital_type,
        value=payload.value,
        unit=payload.unit,
        recorded_at=payload.recorded_at,
        source_document_id=payload.source_document_id,
        created_at=_now(),
    )
    db.add(vital)
    db.commit()
    db.refresh(vital)
    return VitalResponse.model_validate(vital)


@router.put(
    "/{patient_id}/vitals/{vital_id}",
    response_model=VitalResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a vital sign record",
)
def update_vital(
    patient_id: str,
    vital_id: str,
    payload: VitalUpdate,
    db: Session = Depends(get_db),
):
    """PUT /api/v1/patients/{patient_id}/vitals/{vital_id}"""
    _get_patient_or_404(patient_id, db)
    vital = db.query(Vital).filter(
        Vital.id == vital_id, Vital.patient_id == patient_id
    ).first()
    if not vital:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Vital '{vital_id}' not found.")
    _set_fields(vital, payload)
    db.commit()
    db.refresh(vital)
    return VitalResponse.model_validate(vital)


# ── Lab endpoints ─────────────────────────────────────────────────────────────

@router.post(
    "/{patient_id}/labs",
    response_model=LabResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a lab result to a patient record",
)
def create_lab(
    patient_id: str,
    payload: LabCreate,
    db: Session = Depends(get_db),
):
    """POST /api/v1/patients/{patient_id}/labs"""
    _get_patient_or_404(patient_id, db)
    lab = Lab(
        id=_generate_uuid(),
        patient_id=patient_id,
        visit_id=payload.visit_id,
        test_name=payload.test_name,
        result_value=payload.result_value,
        unit=payload.unit,
        reference_range=payload.reference_range,
        test_date=payload.test_date,
        source_document_id=payload.source_document_id,
        created_at=_now(),
    )
    db.add(lab)
    db.commit()
    db.refresh(lab)
    return LabResponse.model_validate(lab)


@router.put(
    "/{patient_id}/labs/{lab_id}",
    response_model=LabResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a lab result record",
)
def update_lab(
    patient_id: str,
    lab_id: str,
    payload: LabUpdate,
    db: Session = Depends(get_db),
):
    """PUT /api/v1/patients/{patient_id}/labs/{lab_id}"""
    _get_patient_or_404(patient_id, db)
    lab = db.query(Lab).filter(
        Lab.id == lab_id, Lab.patient_id == patient_id
    ).first()
    if not lab:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Lab '{lab_id}' not found.")
    _set_fields(lab, payload)
    db.commit()
    db.refresh(lab)
    return LabResponse.model_validate(lab)


# ── Procedure endpoints ───────────────────────────────────────────────────────

@router.post(
    "/{patient_id}/procedures",
    response_model=ProcedureResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a procedure to a patient record",
)
def create_procedure(
    patient_id: str,
    payload: ProcedureCreate,
    db: Session = Depends(get_db),
):
    """POST /api/v1/patients/{patient_id}/procedures"""
    _get_patient_or_404(patient_id, db)
    proc = Procedure(
        id=_generate_uuid(),
        patient_id=patient_id,
        visit_id=payload.visit_id,
        procedure_name=payload.procedure_name,
        procedure_date=payload.procedure_date,
        notes=payload.notes,
        source_document_id=payload.source_document_id,
        created_at=_now(),
    )
    db.add(proc)
    db.commit()
    db.refresh(proc)
    return ProcedureResponse.model_validate(proc)


@router.put(
    "/{patient_id}/procedures/{procedure_id}",
    response_model=ProcedureResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a procedure record",
)
def update_procedure(
    patient_id: str,
    procedure_id: str,
    payload: ProcedureUpdate,
    db: Session = Depends(get_db),
):
    """PUT /api/v1/patients/{patient_id}/procedures/{procedure_id}"""
    _get_patient_or_404(patient_id, db)
    proc = db.query(Procedure).filter(
        Procedure.id == procedure_id, Procedure.patient_id == patient_id
    ).first()
    if not proc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Procedure '{procedure_id}' not found.")
    _set_fields(proc, payload)
    db.commit()
    db.refresh(proc)
    return ProcedureResponse.model_validate(proc)
