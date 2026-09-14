from typing import Any, Dict, List

from pydantic import BaseModel, Field


class NaturalLanguageReportRequest(BaseModel):
    nl_query: str = Field(min_length=1, max_length=1000)


class NaturalLanguageReportResponse(BaseModel):
    chart: Dict[str, Any]
    resolved_filters: Dict[str, Any]
    chart_type: str
    data: List[Dict[str, Any]]
