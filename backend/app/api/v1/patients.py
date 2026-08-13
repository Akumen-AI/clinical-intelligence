from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import get_db
from app.models.patient import Patient
from app.schemas.patient import PatientCreate, PatientUpdate, PatientResponse, AskRequest, AskResponse

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
            
    patient = Patient(
        mrn=patient_in.mrn,
        name=patient_in.name,
        dob=patient_in.dob,
        sex=patient_in.sex
    )
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("", response_model=List[PatientResponse])
def list_patients(search: Optional[str] = None, db: Session = Depends(get_db)):
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
    return query.all()


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(patient_id: str, db: Session = Depends(get_db)):
    """Get a patient by ID."""
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found."
        )
    return patient


@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient(patient_id: str, patient_in: PatientUpdate, db: Session = Depends(get_db)):
    """Update a patient."""
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found."
        )
        
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


@router.post("/{patient_id}/ask", response_model=AskResponse)
def ask_patient_question(patient_id: str, request: AskRequest, db: Session = Depends(get_db)):
    """
    Ask a natural-language question about a specific patient's documents using RAG.
    Retrieval is strictly scoped to this patient's indexed documents.
    """
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found."
        )
        
    from app.services.rag_service import generate_answer
    try:
        answer, source_docs = generate_answer(db, patient_id, request.question)
        return AskResponse(
            answer=answer,
            source_documents=source_docs
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer: {str(e)}"
        )
