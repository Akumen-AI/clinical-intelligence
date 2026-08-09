from __future__ import annotations
import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, model_validator

class CorrectionAction(str, Enum):
    accept = "accept"
    edit   = "edit"
    reject = "reject"

# --- Request ---

class CorrectionLogCreate(BaseModel):
    extracted_field_id: uuid.UUID
    document_id: uuid.UUID
    action: CorrectionAction
    before_value: str | None = None
    after_value: str | None = None   # omit on reject; same as before on accept
    field_name: str
    confidence_score: float | None = Field(None, ge=0.0, le=1.0)
    notes: str | None = None

    @model_validator(mode="after")
    def validate_after_value(self) -> CorrectionLogCreate:
        if self.action == CorrectionAction.accept:
            # accept: after_value must equal before_value (or caller may omit → we fill it)
            if self.after_value is None:
                self.after_value = self.before_value
        if self.action == CorrectionAction.reject:
            # reject: after_value is always None
            self.after_value = None
        return self

# --- Response ---

class CorrectionLogRead(BaseModel):
    id: uuid.UUID
    extracted_field_id: uuid.UUID
    document_id: uuid.UUID
    action: CorrectionAction
    before_value: str | None
    after_value: str | None
    field_name: str
    confidence_score: float | None
    reviewer_id: uuid.UUID
    reviewer_role: str | None
    reviewed_at: datetime
    verified_at: datetime | None
    retraining_exported: bool
    export_batch_id: str | None
    notes: str | None
    created_at: datetime

    model_config = {"from_attributes": True}

# --- Export row (PHI-safe) ---

class CorrectionExportRow(BaseModel):
    """PHI-safe export row for model retraining datasets."""
    log_id: uuid.UUID
    field_id: uuid.UUID          # references only; no raw text exposed
    document_id: uuid.UUID
    field_name: str
    action: CorrectionAction
    # Values are hashed so retraining can detect change without reading PHI
    before_value_hash: str | None  # SHA-256 hex of before_value, or None
    after_value_hash: str | None
    confidence_score: float | None
    reviewer_role: str | None      # role only, never reviewer PII
    reviewed_at: datetime
    verified: bool                  # True if accepted or edited
    export_batch_id: str

class ExportBatchResponse(BaseModel):
    batch_id: str
    exported_count: int
    rows: list[CorrectionExportRow]
