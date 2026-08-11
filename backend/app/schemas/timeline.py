from pydantic import BaseModel
from typing import Optional, List


class TimelineEventSchema(BaseModel):
    event_id: str
    patient_id: Optional[str] = None
    event_date: str
    event_type: str
    summary: str
    document_id: str
    filename: str
    document_type: Optional[str] = None
    source_field_name: str
    confidence_score: float
    verification_status: str


class PatientTimelineResponse(BaseModel):
    patient_id: Optional[str] = None
    total_events: int
    events: List[TimelineEventSchema]
