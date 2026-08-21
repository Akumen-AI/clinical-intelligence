from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class PatientCreate(BaseModel):
    patient_number: Optional[str] = None
    mrn: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[str] = None


class PatientUpdate(BaseModel):
    patient_number: Optional[str] = None
    mrn: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[str] = None
    duplicate_of: Optional[str] = None


class PatientResponse(BaseModel):
    patient_id: str
    patient_number: Optional[str] = None
    mrn: Optional[str] = None
    name: Optional[str] = None
    dob: Optional[str] = None
    sex: Optional[str] = None
    duplicate_of: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MedicationResponse(BaseModel):
    id: str
    raw_text: str
    rxnorm_code: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class DiagnosisResponse(BaseModel):
    id: str
    raw_text: str
    icd10_code: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class LabResultResponse(BaseModel):
    id: str
    raw_text: str
    loinc_code: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class DocumentResponse(BaseModel):
    document_id: str
    filename: str
    document_type: Optional[str] = None
    uploaded_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PatientProfileResponse(BaseModel):
    patient: PatientResponse
    diagnoses: List[DiagnosisResponse] = []
    medications: List[MedicationResponse] = []
    lab_results: List[LabResultResponse] = []
    documents: List[DocumentResponse] = []
    model_config = ConfigDict(from_attributes=True)


class AskRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None


class CitationSchema(BaseModel):
    document_id: str
    snippet: str
    location: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class AskResponse(BaseModel):
    answer: str
    conversation_id: str
    source_documents: List[CitationSchema] = []
    citations: List[CitationSchema] = []

