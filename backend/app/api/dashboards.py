from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import UserRole
from app.core.security import User, get_current_user
from app.schemas.dashboard import DepartmentDashboardResponse, HospitalDashboardResponse
from app.services.dashboard_service import get_department_dashboard, get_hospital_dashboard

router = APIRouter(prefix="/dashboards", tags=["Dashboards"])


def _require_dashboard_access(current_user: User = Depends(get_current_user)):
    if current_user.role not in {UserRole.HOSPITAL_ADMIN, UserRole.DEPARTMENT_HEAD}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: hospital_admin and department_head are the only roles allowed for operational dashboards.",
        )
    return current_user


@router.get("/department", response_model=DepartmentDashboardResponse)
async def department_dashboard(
    department: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _current_user: User = Depends(_require_dashboard_access),
):
    return get_department_dashboard(db, department=department, start_date=start_date, end_date=end_date)


@router.get("/hospital", response_model=HospitalDashboardResponse)
async def hospital_dashboard(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _current_user: User = Depends(_require_dashboard_access),
):
    return get_hospital_dashboard(db, start_date=start_date, end_date=end_date)
