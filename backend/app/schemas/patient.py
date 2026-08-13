from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class PatientCreate(BaseModel):
    mrn: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[str] = None


class PatientUpdate(BaseModel):
    mrn: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[str] = None
    duplicate_of: Optional[str] = None


class PatientResponse(BaseModel):
    patient_id: str
    mrn: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[str] = None
    duplicate_of: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str
    source_documents: List[str]
