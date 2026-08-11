from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.timeline import PatientTimelineResponse, TimelineEventSchema
from app.services.timeline_service import build_patient_timeline

router = APIRouter(prefix="/timeline", tags=["Patient Timeline"])


@router.get("", response_model=PatientTimelineResponse)
def get_timeline(
    patient_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> PatientTimelineResponse:
    """
    Fetch chronological timeline of events across committed documents.
    Optionally filter by patient_id.
    """
    return build_patient_timeline(patient_id=patient_id, db=db)


@router.get("/{document_id}", response_model=TimelineEventSchema)
def get_timeline_event(
    document_id: str,
    db: Session = Depends(get_db),
) -> TimelineEventSchema:
    """
    Fetch single timeline event by source document_id.
    """
    timeline = build_patient_timeline(patient_id=None, db=db)
    for event in timeline.events:
        if event.document_id == document_id:
            return event

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Timeline event for document '{document_id}' not found or document is not committed.",
    )
