from datetime import datetime
from typing import List

from pydantic import BaseModel, ConfigDict, Field


class LayoutRegionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: str
    region_type: str
    bbox: List[float] = Field(min_length=4, max_length=4)
    confidence: float = Field(ge=0.0, le=1.0)
    created_at: datetime
