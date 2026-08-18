"""API router for browsing canonical patient records."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from app.services.rag.rbac_access_guard import RbacAccessGuard, AccessDeniedError

from app.database import get_db
from app.models.canonical_patient_record import CanonicalPatientRecord
from app.models.document import Document
from app.models.extracted_field import ExtractedField
from app.schemas.canonical_record import (
    CanonicalRecordListResponse,
    CanonicalRecordResponse,
)

logger = logging.getLogger("app.api.canonical_records")

router = APIRouter(
    prefix="/canonical-records",
    tags=["Canonical Patient Records"],
)


def _build_response(canonical: CanonicalPatientRecord, doc: Optional[Document], field: Optional[ExtractedField]) -> CanonicalRecordResponse:
    """Map a (CanonicalPatientRecord, Document, ExtractedField) tuple to a response."""
    return CanonicalRecordResponse(
        record_id=canonical.record_id,
        document_id=canonical.document_id,
        field_name=canonical.field_name,
        value=canonical.value,
        source_field_id=canonical.source_field_id,
        created_at=canonical.created_at,
        updated_at=canonical.updated_at,
        filename=doc.filename if doc else None,
        patient_id=doc.patient_id if doc else None,
        document_type=doc.document_type if doc else None,
        confidence_score=field.confidence_score if field else None,
        verification_status=field.verification_status if field else None,
    )


@router.get(
    "",
    response_model=CanonicalRecordListResponse,
    status_code=status.HTTP_200_OK,
    summary="List canonical patient records with optional filters",
)
def list_canonical_records(
    document_id: Optional[str] = Query(default=None, description="Filter by document ID"),
    patient_id: Optional[str] = Query(default=None, description="Filter by patient ID (from joined document)"),
    field_name: Optional[str] = Query(default=None, description="Filter by field name"),
    search: Optional[str] = Query(default=None, description="Free-text search across field names and string values"),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=50, ge=1, le=200, description="Items per page"),
    http_request: Request = None,
    db: Session = Depends(get_db),
):
    """
    GET /api/v1/canonical-records

    Returns a paginated list of all canonical patient records, joined with
    their source document and extracted field metadata.
    """
    try:
        RbacAccessGuard().assert_can_query_patient(http_request.state.user, patient_id)
    except AccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))

    query = (
        db.query(CanonicalPatientRecord, Document, ExtractedField)
        .join(Document, CanonicalPatientRecord.document_id == Document.document_id)
        .outerjoin(ExtractedField, CanonicalPatientRecord.source_field_id == ExtractedField.field_id)
    )

    # Apply filters
    if document_id:
        query = query.filter(CanonicalPatientRecord.document_id == document_id)
    if patient_id:
        query = query.filter(Document.patient_id == patient_id)
    if field_name:
        query = query.filter(CanonicalPatientRecord.field_name == field_name)
    if search:
        like_pattern = f"%{search}%"
        query = query.filter(
            CanonicalPatientRecord.field_name.ilike(like_pattern)
        )

    # Count before pagination
    total = query.count()

    # Order by created_at descending (newest first), then paginate
    offset = (page - 1) * page_size
    results = (
        query.order_by(CanonicalPatientRecord.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )

    items = [_build_response(canonical, doc, field) for canonical, doc, field in results]

    return CanonicalRecordListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{record_id}",
    response_model=CanonicalRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a single canonical record by ID",
)
def get_canonical_record(
    record_id: str,
    http_request: Request,
    db: Session = Depends(get_db),
):
    """
    GET /api/v1/canonical-records/{record_id}

    Returns a single canonical patient record with full document & field context.
    """
    result = (
        db.query(CanonicalPatientRecord, Document, ExtractedField)
        .join(Document, CanonicalPatientRecord.document_id == Document.document_id)
        .outerjoin(ExtractedField, CanonicalPatientRecord.source_field_id == ExtractedField.field_id)
        .filter(CanonicalPatientRecord.record_id == record_id)
        .first()
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Canonical record '{record_id}' not found.",
        )

    canonical, doc, field = result
    
    try:
        RbacAccessGuard().assert_can_query_patient(http_request.state.user, doc.patient_id if doc else None)
    except AccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
        
    return _build_response(canonical, doc, field)
