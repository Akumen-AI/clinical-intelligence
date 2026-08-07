from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.document import Document, DocumentStatus
from app.schemas.extracted_field import DocumentFieldsResponseSchema
from app.services.field_extraction_service import (
    extract_and_persist_fields,
    get_document_fields_response,
)

router = APIRouter(
    prefix="/documents",
    tags=["Key Field Extraction (Epic 2.2 FR-07)"],
)


@router.get(
    "/{document_id}/fields",
    response_model=DocumentFieldsResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get extracted clinical fields",
)
async def get_document_fields(
    document_id: str,
    min_confidence: Optional[float] = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="Return only fields with confidence_score >= this value",
    ),
    max_confidence: Optional[float] = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="Return only fields with confidence_score <= this value",
    ),
    db: Session = Depends(get_db),
):
    """
    GET /api/v1/documents/{document_id}/fields

    Retrieve key clinical fields (patient identifier, vitals, diagnosis, medications,
    dates, ordering physician, lab results) extracted from a printed document.
    Returns a structured JSON schema where missing fields are explicitly null.

    Supports optional confidence-range filtering:
      ?min_confidence=0.0&max_confidence=0.5  → low-confidence fields only
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    response = get_document_fields_response(
        db, document_id,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
    )
    if not response or not response.field_records:
        # Extract on the fly if not yet extracted
        extract_and_persist_fields(db, doc)
        response = get_document_fields_response(
            db, document_id,
            min_confidence=min_confidence,
            max_confidence=max_confidence,
        )

    return response


@router.post(
    "/{document_id}/extract",
    response_model=DocumentFieldsResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Trigger key field extraction",
)
async def extract_document_fields(
    document_id: str,
    db: Session = Depends(get_db),
):
    """
    POST /api/v1/documents/{document_id}/extract

    Manually trigger or re-run key field extraction for a document.
    """
    doc = db.query(Document).filter(Document.document_id == document_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found.",
        )

    doc.status = DocumentStatus.EXTRACTED.value
    db.commit()
    db.refresh(doc)

    extract_and_persist_fields(db, doc)
    response = get_document_fields_response(db, document_id)
    return response
