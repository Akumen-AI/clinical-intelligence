import uuid
import inspect
import asyncio
import structlog
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models.note import Note
from app.core.compliance import enforce_ac3, ComplianceViolationError
from app.schemas.note import NoteCreate, NoteRead

log = structlog.get_logger(__name__)

WRITE_ROLES = {"doctor", "nurse"}
READ_ROLES  = {"doctor", "nurse", "hospital_admin", "department_head"}


async def create_note(
    db,
    payload: NoteCreate,
    author_id: uuid.UUID | str,
    author_role: str,
) -> NoteRead:
    if author_role not in WRITE_ROLES:
        raise PermissionError(f"Role '{author_role}' cannot write notes.")

    # Layer 1: enforce_ac3 before any persistence
    try:
        enforce_ac3(payload.content)
    except ComplianceViolationError as e:
        log.warning("ac3_violation_on_note_save", phrase=e.phrase, author_id=str(author_id))
        raise

    patient_id_val = payload.patient_id if isinstance(payload.patient_id, uuid.UUID) else uuid.UUID(str(payload.patient_id))
    author_id_val = author_id if isinstance(author_id, uuid.UUID) else uuid.UUID(str(author_id))

    note = Note(
        patient_id=patient_id_val,
        author_id=author_id_val,
        author_role=author_role,
        complaint_type=payload.complaint_type,
        content=payload.content,
    )
    db.add(note)
    
    if inspect.iscoroutinefunction(getattr(db, "commit", None)):
        await db.commit()
        await db.refresh(note)
    else:
        db.commit()
        db.refresh(note)

    log.info("note_saved", note_id=str(note.id), patient_id=str(note.patient_id))
    return NoteRead.model_validate(note)


async def list_notes_for_patient(
    db,
    patient_id: uuid.UUID | str,
    requester_role: str,
) -> list[NoteRead]:
    if requester_role not in READ_ROLES:
        raise PermissionError(f"Role '{requester_role}' cannot read notes.")

    patient_id_val = patient_id if isinstance(patient_id, uuid.UUID) else uuid.UUID(str(patient_id))

    if inspect.iscoroutinefunction(getattr(db, "execute", None)):
        result = await db.execute(
            select(Note)
            .where(Note.patient_id == patient_id_val)
            .order_by(Note.created_at.desc())
        )
        notes = result.scalars().all()
    else:
        notes = db.query(Note).filter(Note.patient_id == patient_id_val).order_by(Note.created_at.desc()).all()

    return [NoteRead.model_validate(n) for n in notes]
