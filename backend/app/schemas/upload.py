from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    filename: str
    status: str
    uploaded_at: datetime
    raw_uri: str
    filetype: str
    processed_uri: Optional[str] = None
    processing_time_ms: Optional[int] = None
    document_type: Optional[str] = None
    classification_confidence: Optional[float] = None
    needs_manual_review: Optional[bool] = None

class DocumentUploadItem(BaseModel):
    document_id: str
    filename: str
    status: str
    filetype: str

class UploadSummaryResponse(BaseModel):
    message: str
    uploaded_documents: List[DocumentUploadItem]
    failed_uploads: List[dict] = []

class ErrorDetail(BaseModel):
    filename: str
    error: str
