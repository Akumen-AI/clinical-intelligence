from typing import List, Union, Optional
import mimetypes
import os
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Request, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.upload import (
    DocumentResponse, 
    DocumentUploadItem, 
    RejectedUploadItem,
    UploadSummaryResponse,
    UploadLogResponse,
    ErrorResponseSchema,
    PatientLinkRequest
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
    response_model=UploadSummaryResponse,
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
    background_tasks: BackgroundTasks,
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
            background_tasks.add_task(upload_service.process_document, db, doc.document_id)
            
            accepted_item = DocumentUploadItem(
                document_id=doc.document_id,
                filename=doc.filename,
                status=doc.status,
                filetype=doc.filetype
            )
            return UploadSummaryResponse(
                total_uploaded=1,
                accepted_count=1,
                rejected_count=0,
                accepted=[accepted_item],
                rejected=[]
            )
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
            background_tasks.add_task(upload_service.process_document, db, doc.document_id)
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

@router.get("/{document_id}/file", include_in_schema=False)
async def get_document_file(document_id: str, db: Session = Depends(get_db)):
    """Stream the original uploaded file through an HTTP URL for the reviewer UI."""
    doc = upload_service.get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    raw_path = doc.raw_uri
    if not os.path.isabs(raw_path):
        backend_root = os.path.dirname(upload_service.UPLOAD_DIR)
        raw_path = os.path.join(backend_root, raw_path)
    raw_path = os.path.abspath(raw_path)
    upload_root = os.path.abspath(upload_service.UPLOAD_DIR)
    if os.path.commonpath([raw_path, upload_root]) != upload_root or not os.path.isfile(raw_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Original file is unavailable")

    media_type = mimetypes.guess_type(doc.filename or raw_path)[0] or "application/octet-stream"
    return FileResponse(raw_path, media_type=media_type)

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
            filetype=doc.filetype,
            processed_uri=doc.processed_uri,
            processing_time_ms=doc.processing_time_ms,
            document_type=doc.document_type,
            classification_confidence=doc.classification_confidence,
            needs_manual_review=doc.needs_manual_review
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
        filetype=doc.filetype,
        processed_uri=doc.processed_uri,
        processing_time_ms=doc.processing_time_ms,
        document_type=doc.document_type,
        classification_confidence=doc.classification_confidence,
        needs_manual_review=doc.needs_manual_review
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
    return {
        "document_id": doc.document_id,
        "status": doc.status,
        "document_type": doc.document_type,
        "classification_confidence": doc.classification_confidence,
        "needs_manual_review": doc.needs_manual_review
    }

@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
async def delete_document(document_id: str, db: Session = Depends(get_db)):
    """
    DELETE /api/v1/documents/{document_id}

    Delete a specific document by UUID, removing the database record and associated files.
    """
    deleted = upload_service.delete_document(db, document_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
    return {"message": f"Document '{document_id}' deleted successfully."}

@router.delete("", status_code=status.HTTP_200_OK)
async def delete_all_documents(db: Session = Depends(get_db)):
    """
    DELETE /api/v1/documents

    Delete all documents, removing database records and associated files.
    """
    count = upload_service.delete_all_documents(db)
    return {"message": f"Deleted {count} document(s) successfully.", "count": count}

@router.post("/{document_id}/link-patient", status_code=status.HTTP_200_OK)
async def link_patient(
    document_id: str,
    request: PatientLinkRequest,
    db: Session = Depends(get_db)
):
    """
    POST /api/v1/documents/{document_id}/link-patient
    
    Link a document to a specific patient.
    """
    from app.models.patient import Patient
    
    doc = upload_service.get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID '{document_id}' not found."
        )
        
    patient = db.query(Patient).filter(Patient.patient_id == request.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient with ID '{request.patient_id}' not found."
        )
        
    doc.patient_id = request.patient_id
    db.commit()
    db.refresh(doc)
    
    return {"message": f"Document '{document_id}' linked to patient '{request.patient_id}' successfully."}


