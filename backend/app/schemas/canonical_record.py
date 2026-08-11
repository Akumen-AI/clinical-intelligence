"""Pydantic schemas for the Canonical Patient Record API."""

from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict


class CanonicalRecordResponse(BaseModel):
    """Single canonical record with joined document & extracted-field context."""

    model_config = ConfigDict(from_attributes=True)

    record_id: str
    document_id: str
    field_name: str
    value: Any = None
    source_field_id: str
    created_at: datetime
    updated_at: datetime

    # Joined from Document
    filename: Optional[str] = None
    patient_id: Optional[str] = None
    document_type: Optional[str] = None

    # Joined from ExtractedField
    confidence_score: Optional[float] = None
    verification_status: Optional[str] = None


class CanonicalRecordListResponse(BaseModel):
    """Paginated list of canonical records."""

    items: List[CanonicalRecordResponse]
    total: int
    page: int
    page_size: int
