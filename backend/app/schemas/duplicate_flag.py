from datetime import datetime
from typing import Optional, List, Union
import uuid
from pydantic import BaseModel, ConfigDict, field_serializer


class MergePatientRequest(BaseModel):
    keep_patient_id: str


class PatientDuplicateFlagResponse(BaseModel):
    id: Union[uuid.UUID, str]
    patient_a_id: Union[uuid.UUID, str]
    patient_b_id: Union[uuid.UUID, str]
    similarity_score: float
    match_reasons: List[str]
    status: str
    flagged_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[Union[uuid.UUID, str]] = None
    merged_into_id: Optional[Union[uuid.UUID, str]] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("id", "patient_a_id", "patient_b_id", "resolved_by", "merged_into_id", mode="plain")
    def serialize_uuid(self, v):
        if v is None:
            return None
        return str(v)
