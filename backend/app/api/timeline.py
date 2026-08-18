from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from app.services.rag.rbac_access_guard import RbacAccessGuard, AccessDeniedError
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.timeline import PatientTimelineResponse, TimelineEventSchema
from app.services.timeline_service import build_patient_timeline

router = APIRouter(prefix="/timeline", tags=["Patient Timeline"])


@router.get("", response_model=PatientTimelineResponse)
def get_timeline(
    http_request: Request,
    patient_id: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> PatientTimelineResponse:
    """
    Fetch chronological timeline of events across committed documents.
    Optionally filter by patient_id.
    """
    try:
        RbacAccessGuard().assert_can_query_patient(http_request.state.user, patient_id)
    except AccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        
    return build_patient_timeline(patient_id=patient_id, db=db)


@router.get("/{document_id}", response_model=TimelineEventSchema)
def get_timeline_event(
    document_id: str,
    http_request: Request,
    db: Session = Depends(get_db),
) -> TimelineEventSchema:
    """
    Fetch single timeline event by source document_id.
    """
    from app.models.document import Document
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
        
    try:
        RbacAccessGuard().assert_can_query_patient(http_request.state.user, doc.patient_id)
    except AccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    timeline = build_patient_timeline(patient_id=None, db=db)
    for event in timeline.events:
        if event.document_id == document_id:
            return event

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Timeline event for document '{document_id}' not found or document is not committed.",
    )
