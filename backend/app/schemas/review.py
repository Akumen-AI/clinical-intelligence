from datetime import datetime
from typing import Any, List, Literal, Optional
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


class ReviewActionRequest(BaseModel):
    action: Literal["approve", "reject"]
    reviewer_id: Optional[str] = None


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
