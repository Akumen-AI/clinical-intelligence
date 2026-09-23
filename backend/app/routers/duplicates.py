from typing import List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import get_current_user, User
from app.models.user import UserRole
from app.models.patient_duplicate_flag import PatientDuplicateFlag
from app.schemas.duplicate_flag import PatientDuplicateFlagResponse, MergePatientRequest
from app.services.duplicate_detection import DuplicateDetectionService

router = APIRouter(prefix="/duplicates", tags=["Duplicates"])


def check_admin_role(user: User):
    role_val = getattr(user.role, "value", str(user.role)).lower()
    allowed_admin_roles = {"hospital_admin", "department_head", "admin", "it"}
    if role_val not in allowed_admin_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: role '{role_val}' is not permitted to perform this admin action."
        )


@router.get("", response_model=List[PatientDuplicateFlagResponse])
@router.get("/", response_model=List[PatientDuplicateFlagResponse], include_in_schema=False)
def list_duplicate_flags(
    status_filter: Optional[str] = Query("pending", alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Doctors, Nurses, and Admins may view the duplicate flags queue.
    """
    query = db.query(PatientDuplicateFlag)
    if status_filter:
        query = query.filter(PatientDuplicateFlag.status == status_filter)
    
    flags = query.order_by(PatientDuplicateFlag.flagged_at.desc()).all()
    return flags


@router.post("/{flag_id}/merge")
def merge_duplicate_patients(
    flag_id: str,
    payload: MergePatientRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Merge duplicate patient record. Restricted to admin role only.
    """
    check_admin_role(current_user)
    service = DuplicateDetectionService()
    try:
        keep_patient = service.merge_patients(
            db=db,
            flag_id=flag_id,
            keep_patient_id=payload.keep_patient_id,
            current_user=current_user
        )
        return {
            "status": "success",
            "message": f"Patient merged successfully into {keep_patient.patient_id}",
            "keep_patient_id": keep_patient.patient_id
        }
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/{flag_id}/ignore", response_model=PatientDuplicateFlagResponse)
def ignore_duplicate_flag(
    flag_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Ignore a duplicate flag. Restricted to admin role only.
    """
    check_admin_role(current_user)
    service = DuplicateDetectionService()
    try:
        flag = service.ignore_flag(db=db, flag_id=flag_id, current_user=current_user)
        return flag
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post("/scan")
def trigger_duplicate_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually trigger duplicate detection scan. Restricted to admin role only.
    """
    check_admin_role(current_user)
    service = DuplicateDetectionService()
    created_flags = service.scan_all_patients(db=db)
    return {
        "status": "success",
        "created_flags_count": len(created_flags),
        "created_flags": [str(f.id) for f in created_flags]
    }
