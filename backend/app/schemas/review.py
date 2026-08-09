from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.models.pending_review import ReviewStatus


class PendingReviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    field_name: str
    extracted_value: Optional[Any] = None
    confidence_score: float
    status: ReviewStatus
    reviewer_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime


class PendingReviewListResponse(BaseModel):
    items: List[PendingReviewResponse]
    total: int
    page: int
    page_size: int


class PendingReviewContextResponse(BaseModel):
    """Enriched review item with bounding-box and document metadata for the side-by-side UI."""
    model_config = ConfigDict(from_attributes=True)

    # Core review fields
    id: str
    document_id: str
    field_name: str
    extracted_value: Optional[Any] = None
    confidence_score: float
    status: ReviewStatus
    reviewer_id: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    # Document context
    document_filename: Optional[str] = None
    document_filetype: Optional[str] = None
    raw_uri: Optional[str] = None

    # Bounding box — normalised 0–1 floats {x, y, width, height} or None
    bounding_box: Optional[Dict[str, float]] = None

    # Sibling-field counts for progress display
    total_pending_in_document: Optional[int] = None


class ReviewActionRequest(BaseModel):
    action: Literal["approve", "reject"]
    reviewer_id: Optional[str] = None
    corrected_value: Optional[str] = None  # When set on approve, writes this value instead of extracted_value


class ThresholdConfigRequest(BaseModel):
    threshold: float = Field(..., description="Confidence threshold value (0.0 < threshold <= 1.0)")

    @field_validator("threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not (0.0 < v <= 1.0):
            raise ValueError("Confidence threshold must satisfy 0.0 < threshold <= 1.0")
        return v


class ThresholdConfigResponse(BaseModel):
    threshold: float
    source: str
