from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from datetime import datetime, timezone
from typing import Dict, List

from app.database import get_db
from app.models.patient import Patient
from app.models.clinical_entities import Medication, Allergy, LabResult
from app.schemas.dashboard import PatientDashboardResponse, LabTrendPointSchema, CurrentMedicationSchema
from app.core.patient_access_guard import RbacAccessGuard, AccessDeniedError
from app.services.timeline_service import build_patient_timeline

router = APIRouter(
    prefix="/dashboards",
    tags=["Dashboard"]
)

@router.get("/patient/{patient_id}", response_model=PatientDashboardResponse)
def get_patient_dashboard(
    patient_id: str,
    http_request: Request,
    db: Session = Depends(get_db)
):
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

    # Current Medications
    medications = db.query(Medication).filter(
        Medication.patient_id == patient.patient_id,
        or_(Medication.status == None, Medication.status != 'discontinued')
    ).all()
    
    current_medications = [
        CurrentMedicationSchema(
            id=med.id,
            raw_text=med.raw_text,
            rxnorm_code=med.rxnorm_code,
            status=med.status,
            started_date=med.started_date
        )
        for med in medications
    ]

    # Allergies
    allergies = db.query(Allergy).filter(Allergy.patient_id == patient.patient_id).all()

    # Lab Results & Trends
    all_labs = db.query(LabResult).filter(LabResult.patient_id == patient.patient_id).all()
    
    lab_trends: Dict[str, List[LabTrendPointSchema]] = {}
    other_lab_results = []
    
    for lab in all_labs:
        if lab.value_numeric is not None:
            test_name = lab.test_name or "Unknown Test"
            if test_name not in lab_trends:
                lab_trends[test_name] = []
            
            lab_trends[test_name].append(
                LabTrendPointSchema(
                    date=lab.recorded_at or "Unknown",
                    value=lab.value_numeric,
                    unit=lab.unit,
                    flag=lab.flag
                )
            )
        else:
            other_lab_results.append(lab)

    # Sort each group's points by recorded_at ascending
    for test_name in lab_trends:
        lab_trends[test_name].sort(key=lambda x: x.date if x.date != "Unknown" else "9999-99-99")

    # Timeline
    timeline_response = build_patient_timeline(patient_id=patient.patient_id, db=db)
    
    total_events = timeline_response.total_events
    recent_events = list(reversed(timeline_response.events))[:10]

    return PatientDashboardResponse(
        patient=patient,
        allergies=allergies,
        current_medications=current_medications,
        lab_trends=lab_trends,
        other_lab_results=other_lab_results,
        recent_events=recent_events,
        total_events=total_events,
        generated_at=datetime.now(timezone.utc)
    )
