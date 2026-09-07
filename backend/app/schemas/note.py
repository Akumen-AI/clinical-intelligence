import uuid
from datetime import datetime
from pydantic import BaseModel, field_validator

class NoteCreate(BaseModel):
    patient_id:     uuid.UUID
    complaint_type: str | None = None
    content:        str

    @field_validator("content")
    @classmethod
    def content_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Note content cannot be empty.")
        return v

class NoteRead(BaseModel):
    id:             uuid.UUID
    patient_id:     uuid.UUID
    author_id:      uuid.UUID
    author_role:    str
    complaint_type: str | None
    content:        str
    created_at:     datetime
    updated_at:     datetime

    model_config = {"from_attributes": True}
