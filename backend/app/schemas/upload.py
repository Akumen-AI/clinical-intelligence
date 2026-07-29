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

class DocumentUploadItem(BaseModel):
    document_id: str
    filename: str
    status: str
    filetype: str

class RejectedUploadItem(BaseModel):
    filename: str
    reason: str
    status: str = "REJECTED"

class UploadSummaryResponse(BaseModel):
    total_uploaded: int
    accepted_count: int
    rejected_count: int
    accepted: List[DocumentUploadItem] = []
    rejected: List[RejectedUploadItem] = []

class UploadLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    timestamp: datetime
    reason: Optional[str] = None
    status: str
    client_ip: Optional[str] = None
    http_status: Optional[int] = None

class ErrorResponseSchema(BaseModel):
    detail: str
