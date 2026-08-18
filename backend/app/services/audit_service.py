import uuid
from sqlalchemy.orm import Session
from app.models.audit_log import AuditLogEntry

def write_entry(db: Session, actor_user_id: uuid.UUID, action_type: str, target_entity: str, rationale: str | None = None) -> AuditLogEntry:
    """
    Append an entry to the audit log.
    This is the only sanctioned way to write to the audit log table.
    """
    new_entry = AuditLogEntry(
        actor_user_id=actor_user_id,
        action_type=action_type,
        target_entity=target_entity,
        rationale=rationale
    )
    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    return new_entry
