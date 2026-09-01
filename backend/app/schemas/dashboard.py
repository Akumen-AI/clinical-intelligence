from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class DashboardMetric(BaseModel):
    key: str
    label: str
    value: Optional[Any] = None
    unit: Optional[str] = None
    chart: List[Dict[str, Any]] = []
    series: List[Dict[str, Any]] = []
    available: bool = True
    note: Optional[str] = None


class DashboardFilter(BaseModel):
    department: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class DepartmentDashboardResponse(BaseModel):
    department: Optional[str] = None
    filters: DashboardFilter
    metrics: List[DashboardMetric]


class HospitalDashboardResponse(BaseModel):
    hospital: str = "main"
    filters: DashboardFilter
    metrics: List[DashboardMetric]
