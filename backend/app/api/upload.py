from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.upload import DocumentResponse, DocumentUploadItem, UploadSummaryResponse
from app.services import upload_service

router = APIRouter(
    prefix="/documents",
    tags=["Document Intake (Epic 1.1)"]
)

@router.post("/upload", response_model=List[DocumentUploadItem], status_code=status.HTTP_201_CREATED)
async def upload_documents(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    POST /api/v1/documents/upload
    
    Accepts patient documents (PDF, PNG, JPG, JPEG, TIFF) individually or in bulk.
    Validates file extensions, saves files securely, creates database records,
    and initializes status to new.
    """
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files provided in upload request."
        )

    # First pass validation: fail early if any file has an unsupported format
    for file in files:
        upload_service.validate_file(file)

    results: List[DocumentUploadItem] = []

    for file in files:
        doc = upload_service.queue_document(db, file)
        results.append(
            DocumentUploadItem(
                document_id=doc.document_id,
                filename=doc.filename,
                status=doc.status,
                filetype=doc.filetype
            )
        )

    return results

@router.get("", response_model=List[DocumentResponse])
async def list_documents(db: Session = Depends(get_db)):
    """
    GET /api/v1/documents
    
    Retrieve all uploaded patient documents with document ID, file path, file type, and current pipeline status.
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
