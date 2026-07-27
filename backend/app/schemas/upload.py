from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_id: str
    filename: str
    status: str
    uploaded_at: datetime
    filepath: str
    filetype: str

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
