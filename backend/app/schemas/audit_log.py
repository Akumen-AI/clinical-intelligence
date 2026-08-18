from pydantic import BaseModel
import uuid
from datetime import datetime

class AuditLogResponse(BaseModel):
    log_id: uuid.UUID
    actor_user_id: uuid.UUID
    action_type: str
    target_entity: str
    rationale: str | None = None
    timestamp: datetime

    class Config:
        from_attributes = True
