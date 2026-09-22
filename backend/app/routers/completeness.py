from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import get_current_user, User
from app.models.department_completeness_setting import DepartmentCompletenessSetting
from app.models.user import UserRole
from app.schemas.completeness import (
    CompletenessCheckRequest,
    CompletenessCheckResponse,
    DepartmentSettingIn,
    DepartmentSettingOut,
)
from app.services.completeness_service import CompletenessService

router = APIRouter(prefix="/completeness", tags=["Completeness"])


def check_admin_role(user: User):
    role_val = getattr(user.role, "value", str(user.role)).lower()
    allowed_admin_roles = {"hospital_admin", "department_head", "admin", "it"}
    if role_val not in allowed_admin_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: role '{role_val}' is not permitted to perform this admin action."
        )


@router.post("/check", response_model=CompletenessCheckResponse)
def check_completeness(
    request: CompletenessCheckRequest,
    department_id: UUID = Query(..., description="Department ID to evaluate toggle settings"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check documentation completeness for a patient by complaint type.
    Accessible to Doctors and Admins.
    """
    service = CompletenessService(db)
    try:
        response = service.check(
            patient_id=request.patient_id,
            complaint_type=request.complaint_type,
            department_id=department_id,
        )
        return response
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/settings/{department_id}", response_model=DepartmentSettingOut)
def get_department_setting(
    department_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get completeness feature setting for department. Restricted to Admin roles.
    """
    check_admin_role(current_user)
    dept_str = str(department_id)
    setting = db.query(DepartmentCompletenessSetting).filter(DepartmentCompletenessSetting.department_id == dept_str).first()
    if setting is None:
        return DepartmentSettingOut(department_id=department_id, enabled=True)
    return setting


@router.put("/settings/{department_id}", response_model=DepartmentSettingOut)
def update_department_setting(
    department_id: UUID,
    payload: DepartmentSettingIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update or create completeness feature setting for department. Restricted to Admin roles.
    """
    check_admin_role(current_user)
    dept_str = str(department_id)
    setting = db.query(DepartmentCompletenessSetting).filter(DepartmentCompletenessSetting.department_id == dept_str).first()

    user_id_str = str(current_user.id) if hasattr(current_user, "id") else None

    if setting is None:
        setting = DepartmentCompletenessSetting(
            department_id=dept_str,
            enabled=payload.enabled,
            updated_at=datetime.now(timezone.utc),
            updated_by=user_id_str,
        )
        db.add(setting)
    else:
        setting.enabled = payload.enabled
        setting.updated_at = datetime.now(timezone.utc)
        setting.updated_by = user_id_str

    db.commit()
    db.refresh(setting)
    return setting
