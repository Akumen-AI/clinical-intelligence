from typing import List, Dict, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.schemas.patient import PatientResponse, AllergyResponse, LabResultResponse
from app.schemas.timeline import TimelineEventSchema

class LabTrendPointSchema(BaseModel):
    date: str
    value: float
    unit: Optional[str] = None
    flag: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class CurrentMedicationSchema(BaseModel):
    id: str
    raw_text: str
    rxnorm_code: Optional[str] = None
    status: Optional[str] = None
    started_date: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)

class PatientDashboardResponse(BaseModel):
    patient: PatientResponse
    allergies: List[AllergyResponse] = []
    current_medications: List[CurrentMedicationSchema] = []
    lab_trends: Dict[str, List[LabTrendPointSchema]] = {}
    other_lab_results: List[LabResultResponse] = []
    recent_events: List[TimelineEventSchema] = []
    total_events: int
    generated_at: datetime
    model_config = ConfigDict(from_attributes=True)
