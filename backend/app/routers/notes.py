import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from app.database import get_db
from app.core.rbac import check_rbac
from app.schemas.note import NoteCreate, NoteRead
from app.services.notes_service import create_note, list_notes_for_patient
from app.core.compliance import ComplianceViolationError

router = APIRouter(prefix="/api/v1/notes", tags=["notes"])


@router.post("", response_model=NoteRead, status_code=status.HTTP_201_CREATED)
async def add_note(
    payload: NoteCreate,
    current_user=Depends(check_rbac),
    db=Depends(get_db),
):
    try:
        author_role = getattr(current_user.role, "value", current_user.role)
        return await create_note(
            db=db,
            payload=payload,
            author_id=current_user.id,
            author_role=str(author_role),
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ComplianceViolationError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Note rejected by AC-3 compliance check: {e.phrase}",
        )


@router.get("/{patient_id}", response_model=list[NoteRead])
async def get_notes(
    patient_id: uuid.UUID,
    current_user=Depends(check_rbac),
    db=Depends(get_db),
):
    try:
        requester_role = getattr(current_user.role, "value", current_user.role)
        return await list_notes_for_patient(
            db=db,
            patient_id=patient_id,
            requester_role=str(requester_role),
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
