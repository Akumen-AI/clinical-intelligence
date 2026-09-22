import uuid
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLogEntry
from app.core.context import get_correlation_id

# Represents scheduled/system-triggered actions with no human actor
SYSTEM_ACTOR_ID = uuid.UUID('ffffffff-ffff-ffff-ffff-ffffffffffff')

def _build_entry(actor_user_id: uuid.UUID, action_type: str, target_entity: str, rationale: str | None = None, patient_id: str | None = None, outcome: str | None = None, context: dict | None = None) -> AuditLogEntry:
    return AuditLogEntry(
        actor_user_id=actor_user_id,
        action_type=action_type,
        target_entity=target_entity,
        rationale=rationale,
        patient_id=patient_id,
        correlation_id=get_correlation_id(),
        outcome=outcome,
        context=context
    )

def write_entry(db: Session, actor_user_id: uuid.UUID, action_type: str, target_entity: str, rationale: str | None = None, patient_id: str | None = None, outcome: str | None = None, context: dict | None = None) -> AuditLogEntry:
    """
    Append an entry to the audit log (sync).
    This (and write_entry_async) is the only sanctioned way to write to the audit log table.
    """
    new_entry = _build_entry(actor_user_id, action_type, target_entity, rationale, patient_id, outcome, context)
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry



# Removed backfill_patient_id_for_document per append-only requirements.
