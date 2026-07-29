from typing import List, Union, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.upload import (
    DocumentResponse, 
    DocumentUploadItem, 
    RejectedUploadItem,
    UploadSummaryResponse,
    UploadLogResponse,
    ErrorResponseSchema
)
from app.services import upload_service
from app.services.validation_service import ValidationService
from app.utils.validators import FileValidationError

router = APIRouter(
    prefix="/documents",
    tags=["Document Intake & Validation (Epic 1.1 & 1.3)"]
)

@router.post(
    "/upload",
    response_model=Union[UploadSummaryResponse, List[DocumentUploadItem]],
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {
            "model": ErrorResponseSchema,
            "description": "Validation failed: Unsupported file type, corrupted file, empty file, or oversized file."
        }
    }
)
async def upload_documents(
    request: Request,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    POST /api/v1/documents/upload
    
    Accepts clinical documents (PDF, PNG, JPG, JPEG, TIFF) individually or in bulk.
    Validates file extensions, MIME types, sizes (<20MB), and file readability/corruption before queueing.
    
    - Invalid files are REJECTED, recorded in `UploadLog`, and barred from queueing.
    - Valid files are saved, assigned `QUEUED` status, recorded in `UploadLog`, and queued for processing.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided in upload request."
        )

    client_ip = request.client.host if request.client else "unknown"

    # Single File Upload Flow
    if len(files) == 1:
        file = files[0]
        try:
            doc = await upload_service.process_single_upload(db, file, client_ip)
            return [
                DocumentUploadItem(
                    document_id=doc.document_id,
                    filename=doc.filename,
                    status=doc.status,
                    filetype=doc.filetype
                )
            ]
        except FileValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=e.message
            )

    # Multi-File Bulk Upload Flow
    accepted_items: List[DocumentUploadItem] = []
    rejected_items: List[RejectedUploadItem] = []

    for file in files:
        try:
            doc = await upload_service.process_single_upload(db, file, client_ip)
            accepted_items.append(
                DocumentUploadItem(
                    document_id=doc.document_id,
                    filename=doc.filename,
                    status=doc.status,
                    filetype=doc.filetype
                )
            )
        except FileValidationError as e:
            rejected_items.append(
                RejectedUploadItem(
                    filename=file.filename or "unknown",
                    reason=e.message,
                    status="REJECTED"
                )
            )

    # If all files failed validation in a multi-file upload, raise HTTP 400 with first failure reason or summary
    if len(accepted_items) == 0 and len(rejected_items) > 0:
        first_reason = rejected_items[0].reason
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"All files rejected: {first_reason}" if len(rejected_items) == 1 else f"Validation failed for all uploaded files. Reason: {first_reason}"
        )

    return UploadSummaryResponse(
        total_uploaded=len(files),
        accepted_count=len(accepted_items),
        rejected_count=len(rejected_items),
        accepted=accepted_items,
        rejected=rejected_items
    )

@router.get("/upload-logs", response_model=List[UploadLogResponse])
async def get_upload_logs(
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/documents/upload-logs
    
    Retrieve audit history of all accepted and rejected file upload attempts.
    """
    return ValidationService.get_upload_logs(db, limit=limit)

@router.get("", response_model=List[DocumentResponse])
async def list_documents(db: Session = Depends(get_db)):
    """
    GET /api/v1/documents
    
    Retrieve all uploaded patient documents with document ID, file path, file type, and pipeline status.
    """
    docs = upload_service.get_all_documents(db)
    return [
        DocumentResponse(
            document_id=doc.document_id,
            filename=doc.filename,
            status=doc.status,
            uploaded_at=doc.uploaded_at,
            raw_uri=doc.raw_uri,
            filetype=doc.filetype
        )
        for doc in docs
    ]

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: str, db: Session = Depends(get_db)):
    """
    GET /api/v1/documents/{document_id}
    
    Retrieve specific document metadata by UUID.
    """
    doc = upload_service.get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
    return DocumentResponse(
        document_id=doc.document_id,
        filename=doc.filename,
        status=doc.status,
        uploaded_at=doc.uploaded_at,
        raw_uri=doc.raw_uri,
        filetype=doc.filetype
    )

@router.get("/{document_id}/status")
async def get_document_status(document_id: str, db: Session = Depends(get_db)):
    """
    GET /api/v1/documents/{document_id}/status
    
    Poll pipeline stage for one document.
    """
    doc = upload_service.get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
    return {"document_id": doc.document_id, "status": doc.status}
