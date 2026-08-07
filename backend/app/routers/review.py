from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.pending_review import PendingReview, ReviewStatus
from app.schemas.review import (
    PendingReviewListResponse,
    PendingReviewResponse,
    ReviewActionRequest,
    ThresholdConfigRequest,
    ThresholdConfigResponse,
)
from app.services import canonical_record_service
from app.services.confidence_router import (
    get_confidence_threshold_info,
    set_confidence_threshold,
)

router = APIRouter(
    prefix="/review",
    tags=["Confidence Routing & Pending Review (Epic 2.5 FR-10)"],
)


@router.get(
    "/pending",
    response_model=PendingReviewListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get paginated list of pending review fields",
)
def get_pending_reviews(
    document_id: Optional[str] = Query(
        default=None,
        description="Optional filter by document ID",
    ),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
):
    """
    GET /api/v1/review/pending

    Returns a paginated list of fields queued for human verification (status=PENDING only).
    APPROVED and REJECTED records are filtered out by default.
    """
    query = db.query(PendingReview).filter(PendingReview.status == ReviewStatus.PENDING)

    if document_id:
        query = query.filter(PendingReview.document_id == document_id)

    total = query.count()
    offset = (page - 1) * page_size
    records = (
        query.order_by(PendingReview.created_at.asc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = [PendingReviewResponse.model_validate(rec) for rec in records]
    return PendingReviewListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.patch(
    "/pending/{review_id}",
    response_model=PendingReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve or reject a pending field review",
)
def review_pending_field(
    review_id: str,
    payload: ReviewActionRequest,
    db: Session = Depends(get_db),
):
    """
    PATCH /api/v1/review/pending/{review_id}

    Updates status of a pending review item to APPROVED or REJECTED.
    On approve, automatically writes the field to the canonical patient record.
    """
    review_rec = (
        db.query(PendingReview)
        .filter(PendingReview.id == review_id)
        .first()
    )
    if not review_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending review record with ID '{review_id}' not found.",
        )

    if payload.action == "approve":
        review_rec.status = ReviewStatus.APPROVED
        # Write to canonical record on approval
        canonical_record_service.upsert_field(
            document_id=review_rec.document_id,
            field_name=review_rec.field_name,
            value=review_rec.extracted_value,
            confidence=review_rec.confidence_score,
            db=db,
        )
    elif payload.action == "reject":
        review_rec.status = ReviewStatus.REJECTED

    if payload.reviewer_id:
        review_rec.reviewer_id = payload.reviewer_id

    review_rec.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review_rec)

    return PendingReviewResponse.model_validate(review_rec)


@router.get(
    "/config/threshold",
    response_model=ThresholdConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Get active confidence routing threshold",
)
def get_threshold_config(db: Session = Depends(get_db)):
    """
    GET /api/v1/review/config/threshold

    Returns current confidence routing threshold value and its source (env or db).
    """
    val, source = get_confidence_threshold_info(db)
    return ThresholdConfigResponse(threshold=val, source=source)


@router.put(
    "/config/threshold",
    response_model=ThresholdConfigResponse,
    status_code=status.HTTP_200_OK,
    summary="Update confidence routing threshold",
)
def update_threshold_config(
    payload: ThresholdConfigRequest,
    db: Session = Depends(get_db),
):
    """
    PUT /api/v1/review/config/threshold

    Updates the confidence threshold (must be 0.0 < threshold <= 1.0) and persists to DB.
    """
    try:
        val, source = set_confidence_threshold(payload.threshold, db=db)
        return ThresholdConfigResponse(threshold=val, source=source)
    except ValueError as val_err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(val_err),
        )
