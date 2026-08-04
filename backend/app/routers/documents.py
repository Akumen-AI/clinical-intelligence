from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.extraction_field import ExtractionField

router = APIRouter(tags=["Documents"])


class FieldConfidenceItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    field_id: str
    field_name: str
    raw_value: Optional[str] = None
    confidence: float
    status: str


class ConfidenceSummary(BaseModel):
    total_fields: int
    auto_approved: int
    pending_review: int
    mean_confidence: float


class DocumentFieldsResponse(BaseModel):
    document_id: str
    fields: List[FieldConfidenceItem]
    confidence_summary: ConfidenceSummary


@router.get(
    "/documents/{document_id}/fields",
    response_model=DocumentFieldsResponse,
    summary="Get document extracted fields with confidence scores and status summary"
)
def get_document_fields(document_id: str, db: Session = Depends(get_db)):
    """
    Retrieve all extracted fields for a given document_id along with per-field
    confidence scores, status, and overall confidence summary.
    """
    field_records = db.query(ExtractionField).filter(
        ExtractionField.document_id == document_id
    ).all()

    fields_list = []
    total_fields = len(field_records)
    auto_approved_count = 0
    pending_review_count = 0
    sum_confidence = 0.0

    for f in field_records:
        conf = float(f.confidence) if f.confidence is not None else 0.0
        sum_confidence += conf

        if f.status == "auto_approved":
            auto_approved_count += 1
        elif f.status == "pending_review":
            pending_review_count += 1

        fields_list.append(
            FieldConfidenceItem(
                field_id=f.field_id,
                field_name=f.field_name,
                raw_value=f.raw_value,
                confidence=conf,
                status=f.status or "pending_review"
            )
        )

    mean_conf = round(sum_confidence / total_fields, 2) if total_fields > 0 else 0.0

    summary = ConfidenceSummary(
        total_fields=total_fields,
        auto_approved=auto_approved_count,
        pending_review=pending_review_count,
        mean_confidence=mean_conf
    )

    return DocumentFieldsResponse(
        document_id=document_id,
        fields=fields_list,
        confidence_summary=summary
    )
