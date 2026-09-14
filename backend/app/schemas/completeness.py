from uuid import UUID
from typing import Optional, List, Union
from pydantic import BaseModel, ConfigDict, field_serializer


class CompletenessCheckRequest(BaseModel):
    patient_id: UUID
    complaint_type: str   # must match a key in COMPLAINT_CHECKLISTS


class MissingFieldItem(BaseModel):
    field_label: str      # human-readable, never diagnostic


class CompletenessCheckResponse(BaseModel):
    patient_id: UUID
    complaint_type: str
    missing_fields: List[MissingFieldItem]
    total_required: int
    total_documented: int
    feature_enabled: bool

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("patient_id", mode="plain")
    def serialize_uuid(self, v):
        if v is None:
            return None
        return str(v)


class DepartmentSettingIn(BaseModel):
    enabled: bool


class DepartmentSettingOut(BaseModel):
    department_id: Union[UUID, str]
    enabled: bool

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("department_id", mode="plain")
    def serialize_uuid(self, v):
        if v is None:
            return None
        return str(v)
