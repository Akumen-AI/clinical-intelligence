import io
import os
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from PIL import Image

from app.database import get_db
from app.models.document import Document
from app.models.extracted_field import ExtractedField
from app.models.pending_review import PendingReview, ReviewStatus
from app.schemas.review import (
    PendingReviewContextResponse,
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

logger = logging.getLogger("app.routers.review")

router = APIRouter(
    prefix="/review",
    tags=["Confidence Routing & Pending Review (Epic 2.5 FR-10)"],
)

# ── helpers ────────────────────────────────────────────────────────────────────

def _upload_base_dir() -> str:
    """Return the absolute path to the uploads directory."""
    from app.services.upload_service import ensure_upload_directory_exists
    return ensure_upload_directory_exists()


def _resolve_doc_path(raw_uri: str) -> str:
    """Convert a raw_uri like 'uploads/xyz_file.png' to an absolute filesystem path."""
    uploads_dir = _upload_base_dir()
    # raw_uri may be 'uploads/<filename>' or an absolute path
    if os.path.isabs(raw_uri):
        return raw_uri
    # Strip leading 'uploads/' prefix if present
    relative = raw_uri.lstrip("/")
    if relative.startswith("uploads/"):
        relative = relative[len("uploads/"):]
    return os.path.join(uploads_dir, relative)


def _render_document_image(raw_uri: str, filetype: str) -> Image.Image:
    """
    Return a PIL Image for the document.
    PDFs are converted from page 1; images are opened directly.
    """
    abs_path = _resolve_doc_path(raw_uri)

    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Document file not found at: {abs_path}")

    ft = (filetype or "").lower().strip(".")
    if ft == "pdf":
        try:
            from pdf2image import convert_from_path
            pages = convert_from_path(abs_path, dpi=150, first_page=1, last_page=1)
            if not pages:
                raise ValueError("PDF produced no pages")
            return pages[0]
        except Exception as e:
            logger.warning(f"pdf2image failed ({e}); falling back to blank image")
            img = Image.new("RGB", (800, 1100), color=(240, 240, 240))
            return img
    else:
        return Image.open(abs_path).convert("RGB")


def _crop_region(img: Image.Image, bbox: Optional[dict], padding: float = 0.02) -> Image.Image:
    """
    Crop the image to the bounding box region with padding.
    bbox keys: x, y, width, height — all normalised 0-1 floats.
    If bbox is None or invalid, returns the full image.
    """
    if not bbox:
        return img

    try:
        w, h = img.size
        x = float(bbox.get("x", 0))
        y = float(bbox.get("y", 0))
        bw = float(bbox.get("width", 1))
        bh = float(bbox.get("height", 1))

        # Apply padding
        x1 = max(0.0, x - padding)
        y1 = max(0.0, y - padding)
        x2 = min(1.0, x + bw + padding)
        y2 = min(1.0, y + bh + padding)

        left = int(x1 * w)
        top = int(y1 * h)
        right = int(x2 * w)
        bottom = int(y2 * h)

        cropped = img.crop((left, top, right, bottom))
        return cropped if cropped.size[0] > 0 and cropped.size[1] > 0 else img
    except Exception:
        return img


# ── endpoints ──────────────────────────────────────────────────────────────────

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


@router.get(
    "/pending/{review_id}/context",
    response_model=PendingReviewContextResponse,
    status_code=status.HTTP_200_OK,
    summary="Get enriched review item with document and bounding box context",
)
def get_review_context(
    review_id: str,
    db: Session = Depends(get_db),
):
    """
    GET /api/v1/review/pending/{review_id}/context

    Returns the pending review record joined with document metadata and the
    bounding box from the corresponding ExtractedField row (if any).
    Used by the side-by-side review UI to avoid multiple round-trips.
    """
    review_rec = (
        db.query(PendingReview)
        .filter(PendingReview.id == review_id)
        .first()
    )
    if not review_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending review record '{review_id}' not found.",
        )

    # Fetch associated document
    doc = db.query(Document).filter(Document.document_id == review_rec.document_id).first()

    # Fetch bounding box from ExtractedField (most recent match)
    extracted = (
        db.query(ExtractedField)
        .filter(
            ExtractedField.document_id == review_rec.document_id,
            ExtractedField.field_name == review_rec.field_name,
        )
        .order_by(ExtractedField.created_at.desc())
        .first()
    )

    # Count sibling pending items in the same document
    sibling_count = (
        db.query(PendingReview)
        .filter(
            PendingReview.document_id == review_rec.document_id,
            PendingReview.status == ReviewStatus.PENDING,
        )
        .count()
    )

    return PendingReviewContextResponse(
        id=review_rec.id,
        document_id=review_rec.document_id,
        field_name=review_rec.field_name,
        extracted_value=review_rec.extracted_value,
        confidence_score=review_rec.confidence_score,
        status=review_rec.status,
        reviewer_id=review_rec.reviewer_id,
        reviewed_at=review_rec.reviewed_at,
        created_at=review_rec.created_at,
        document_filename=doc.filename if doc else None,
        document_filetype=doc.filetype if doc else None,
        raw_uri=doc.raw_uri if doc else None,
        bounding_box=extracted.bounding_box if extracted else None,
        total_pending_in_document=sibling_count,
    )


@router.get(
    "/pending/{review_id}/image",
    status_code=status.HTTP_200_OK,
    summary="Get document image region for a pending review field",
    responses={200: {"content": {"image/jpeg": {}}}},
)
def get_review_image(
    review_id: str,
    full_page: bool = Query(
        default=False,
        description="If true, return the full document page instead of the cropped region",
    ),
    db: Session = Depends(get_db),
):
    """
    GET /api/v1/review/pending/{review_id}/image

    Returns a JPEG image of the document region corresponding to the field under review.
    - If the ExtractedField has a bounding_box, returns a padded crop of that region.
    - Otherwise returns the full document page.
    PDFs are rendered to PNG via pdf2image (page 1).
    """
    review_rec = (
        db.query(PendingReview)
        .filter(PendingReview.id == review_id)
        .first()
    )
    if not review_rec:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pending review record '{review_id}' not found.",
        )

    doc = db.query(Document).filter(Document.document_id == review_rec.document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{review_rec.document_id}' not found.",
        )

    # Get bounding box
    bbox = None
    if not full_page:
        extracted = (
            db.query(ExtractedField)
            .filter(
                ExtractedField.document_id == review_rec.document_id,
                ExtractedField.field_name == review_rec.field_name,
            )
            .order_by(ExtractedField.created_at.desc())
            .first()
        )
        bbox = extracted.bounding_box if extracted else None

    try:
        img = _render_document_image(doc.raw_uri, doc.filetype)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error(f"[ReviewImage] Failed to render document image: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to render document image: {exc}",
        )

    result_img = _crop_region(img, bbox) if (bbox and not full_page) else img

    # Convert to JPEG bytes
    buf = io.BytesIO()
    result_img.save(buf, format="JPEG", quality=88, optimize=True)
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/jpeg")


@router.patch(
    "/pending/{review_id}",
    response_model=PendingReviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve, edit-and-approve, or reject a pending field review",
)
def review_pending_field(
    review_id: str,
    payload: ReviewActionRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    PATCH /api/v1/review/pending/{review_id}

    Updates status of a pending review item to APPROVED or REJECTED.
    On approve, automatically writes the field to the canonical patient record.
    If `corrected_value` is provided alongside action=approve, that value is
    written to the canonical record instead of the originally extracted value.
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
        # Use corrected value when reviewer edited, otherwise fall back to extracted
        value_to_write = (
            payload.corrected_value
            if payload.corrected_value is not None
            else review_rec.extracted_value
        )
        canonical_record_service.upsert_field(
            document_id=review_rec.document_id,
            field_name=review_rec.field_name,
            value=value_to_write,
            confidence=review_rec.confidence_score,
            db=db,
            human_verified=True,
        )
    elif payload.action == "reject":
        review_rec.status = ReviewStatus.REJECTED

    if payload.reviewer_id:
        review_rec.reviewer_id = payload.reviewer_id

    review_rec.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review_rec)

    # Trigger background indexing if document is already linked to a patient
    doc = db.query(Document).filter(Document.document_id == review_rec.document_id).first()
    if doc and doc.patient_id:
        from app.tasks.rag_tasks import index_document_task
        background_tasks.add_task(index_document_task, doc.document_id)

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
