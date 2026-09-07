import uuid
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLogEntry

# Represents scheduled/system-triggered actions with no human actor
SYSTEM_ACTOR_ID = uuid.UUID('ffffffff-ffff-ffff-ffff-ffffffffffff')

def _build_entry(actor_user_id: uuid.UUID, action_type: str, target_entity: str, rationale: str | None = None, patient_id: str | None = None) -> AuditLogEntry:
    return AuditLogEntry(
        actor_user_id=actor_user_id,
        action_type=action_type,
        target_entity=target_entity,
        rationale=rationale,
        patient_id=patient_id
    )

def write_entry(db: Session, actor_user_id: uuid.UUID, action_type: str, target_entity: str, rationale: str | None = None, patient_id: str | None = None) -> AuditLogEntry:
    """
    Append an entry to the audit log (sync).
    This (and write_entry_async) is the only sanctioned way to write to the audit log table.
    """
    new_entry = _build_entry(actor_user_id, action_type, target_entity, rationale, patient_id)
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry

async def write_entry_async(db: AsyncSession, actor_user_id: uuid.UUID, action_type: str, target_entity: str, rationale: str | None = None, patient_id: str | None = None) -> AuditLogEntry:
    """
    Append an entry to the audit log (async).
    This (and write_entry) is the only sanctioned way to write to the audit log table.
    """
    new_entry = _build_entry(actor_user_id, action_type, target_entity, rationale, patient_id)
    db.add(new_entry)
    await db.flush()
    await db.commit()
    await db.refresh(new_entry)
    return new_entry

def backfill_patient_id_for_document(db: Session, document_id: str, patient_id: str):
    """
    Backfill patient_id onto existing audit log entries for a document and its related records.
    This only affects rows where patient_id is currently NULL.
    """
    from app.models.canonical_patient_record import CanonicalPatientRecord
    from app.models.pending_review import PendingReview

    # 1. Document entries
    db.query(AuditLogEntry).filter(
        AuditLogEntry.target_entity == f"document:{document_id}",
        AuditLogEntry.patient_id.is_(None)
    ).update({"patient_id": patient_id}, synchronize_session=False)

    # 2. Canonical record entries
    canonical_ids = db.query(CanonicalPatientRecord.record_id).filter(
        CanonicalPatientRecord.document_id == document_id
    ).all()
    if canonical_ids:
        canonical_entities = [f"canonical_record:{r[0]}" for r in canonical_ids]
        db.query(AuditLogEntry).filter(
            AuditLogEntry.target_entity.in_(canonical_entities),
            AuditLogEntry.patient_id.is_(None)
        ).update({"patient_id": patient_id}, synchronize_session=False)

    # 3. Pending review entries
    review_ids = db.query(PendingReview.id).filter(
        PendingReview.document_id == document_id
    ).all()
    if review_ids:
        review_entities = [f"pending_review:{r[0]}" for r in review_ids]
        db.query(AuditLogEntry).filter(
            AuditLogEntry.target_entity.in_(review_entities),
            AuditLogEntry.patient_id.is_(None)
        ).update({"patient_id": patient_id}, synchronize_session=False)

    db.commit()
