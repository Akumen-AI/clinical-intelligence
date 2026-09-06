from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.patient import Patient
from app.models.document import Document
from app.models.clinical_entities import Diagnosis, Medication, LabResult
from app.schemas.patient import PatientCreate, PatientUpdate, PatientResponse, PatientProfileResponse, AskRequest, AskResponse
from app.core.security import User
from app.models.user import UserRole
from app.core.patient_access_guard import RbacAccessGuard, AccessDeniedError
from fastapi import Request
from app.services.context_panel_service import ContextPanelService

router = APIRouter(
    prefix="/patients",
    tags=["Patient Identity"]
)


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(patient_in: PatientCreate, db: Session = Depends(get_db)):
    """Create a new patient record."""
    if patient_in.mrn:
        existing = db.query(Patient).filter(Patient.mrn == patient_in.mrn).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Patient with MRN '{patient_in.mrn}' already exists."
            )
            
    patient_number = patient_in.patient_number
    if not patient_number:
        count = db.query(Patient).count()
        patient_number = f"PT-{1001 + count}"

    patient = Patient(
        patient_number=patient_number,
        mrn=patient_in.mrn,
        name=patient_in.name,
        dob=patient_in.dob,
        sex=patient_in.sex
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}/records", response_model=PatientProfileResponse)
def get_patient_records(
    patient_id: str,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """Get a full patient profile including related clinical records."""
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found."
        )

    current_user = http_request.state.user
    try:
        RbacAccessGuard().assert_can_query_patient(current_user, patient.patient_id)
    except AccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    documents = db.query(Document).filter(Document.patient_id == patient_id).all()
    diagnoses = db.query(Diagnosis).filter(Diagnosis.patient_id == patient_id).all()
    medications = db.query(Medication).filter(Medication.patient_id == patient_id).all()
    lab_results = db.query(LabResult).filter(LabResult.patient_id == patient_id).all()

    return {
        "patient": patient,
        "documents": documents,
        "diagnoses": diagnoses,
        "medications": medications,
        "lab_results": lab_results
    }


@router.get("", response_model=List[PatientResponse])
def list_patients(
    http_request: Request,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all patients with optional search by name or MRN."""
    query = db.query(Patient)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                Patient.name.ilike(search_term),
                Patient.mrn.ilike(search_term)
            )
        )
        
    current_user = http_request.state.user
    user_role = getattr(current_user, "role", None)
    if user_role in (UserRole.DOCTOR, UserRole.NURSE, "doctor", "nurse"):
        access_list = getattr(current_user, "patient_access", []) or []
        query = query.filter(Patient.patient_id.in_(access_list))
    elif user_role in (UserRole.DEPARTMENT_HEAD, "department_head"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Department Head is not authorized to list patient records.")
        
    return query.all()


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: str,
    http_request: Request,
    db: Session = Depends(get_db)
):
    """Get a patient by ID, MRN, or OP ID."""
    patient = db.query(Patient).filter(
        or_(
            Patient.patient_id == patient_id,
            Patient.patient_number == patient_id,
            Patient.mrn == patient_id
        )
    ).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found."
        )

    current_user = http_request.state.user
    try:
        RbacAccessGuard().assert_can_query_patient(current_user, patient.patient_id)
    except AccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    return patient


@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient(patient_id: str, patient_in: PatientUpdate, http_request: Request, db: Session = Depends(get_db)):
    """Update a patient."""
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found."
        )
        
    current_user = http_request.state.user
    try:
        RbacAccessGuard().assert_can_query_patient(current_user, patient.patient_id)
    except AccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        
    if patient_in.mrn and patient_in.mrn != patient.mrn:
        existing = db.query(Patient).filter(Patient.mrn == patient_in.mrn).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Patient with MRN '{patient_in.mrn}' already exists."
            )

    update_data = patient_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(patient, key, value)
        
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/{patient_id}/context-panel")
def get_context_panel(
    patient_id: str,
    http_request: Request,
    db: Session = Depends(get_db),
):
    """
    Story 10.1 / FR-32 — Proactive context panel.

    Returns medications, allergies, prior lab results, and history
    sourced exclusively from the canonical record.

    AC-3 contract: Diagnoses are NEVER included in this response.
    No icd10_code or condition label is returned.
    """
    # ── RBAC gate (must be first) ──────────────────────────────────────
    patient = db.query(Patient).filter(
        or_(
            Patient.patient_id == patient_id,
            Patient.patient_number == patient_id,
            Patient.mrn == patient_id,
        )
    ).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")

    current_user = http_request.state.user
    try:
        RbacAccessGuard().assert_can_query_patient(current_user, patient.patient_id)
    except AccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    # ── Build panel (AC-2: canonical DB only, AC-3: no diagnoses) ─────
    panel = ContextPanelService().build_context(db, patient.patient_id)
    return panel.to_dict()


@router.post("/{patient_id}/ask", response_model=AskResponse)
def ask_patient_question(
    patient_id: str, 
    request: AskRequest, 
    http_request: Request,
    db: Session = Depends(get_db)
):
    """
    Ask a natural-language question about a specific patient's documents using RAG.
    Retrieval is strictly scoped to this patient's indexed documents.
    """
    patient = db.query(Patient).filter(
        or_(
            Patient.patient_id == patient_id,
            Patient.patient_number == patient_id,
            Patient.mrn == patient_id
        )
    ).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found."
        )

    current_user = http_request.state.user

    try:
        RbacAccessGuard().assert_can_query_patient(current_user, patient.patient_id)
    except AccessDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
        
    from app.services.rag_service import generate_answer
    from app.services import audit_service
    try:
        answer, citations, conv_id = generate_answer(
            db=db, 
            patient_id=patient.patient_id, 
            question=request.question,
            user_id=current_user.id,
            conversation_id=request.conversation_id
        )
        
        has_answer = len(citations) > 0
        audit_service.write_entry(
            db=db,
            actor_user_id=current_user.id,
            action_type="rag_query",
            target_entity=f"patient:{patient.patient_id}",
            rationale=f"Asked: '{request.question}'. Grounded answer found: {has_answer}"
        )
        
        return AskResponse(
            answer=answer,
            conversation_id=conv_id,
            source_documents=citations,
            citations=citations
        )
    except AccessDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer: {str(e)}"
        )
