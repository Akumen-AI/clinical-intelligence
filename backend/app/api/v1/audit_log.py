from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import uuid

from app.database import get_db
from app.models.audit_log import AuditLogEntry
from app.schemas.audit_log import AuditLogResponse

router = APIRouter()

@router.get("", response_model=List[AuditLogResponse])
def get_audit_logs(
    actor_user_id: uuid.UUID = None,
    action_type: str = None,
    start_date: datetime = None,
    end_date: datetime = None,
    skip: int = 0,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """
    Retrieve audit logs. Can be filtered by actor, action type, and date range.
    """
    query = db.query(AuditLogEntry)
    
    if actor_user_id:
        query = query.filter(AuditLogEntry.actor_user_id == actor_user_id)
    if action_type:
        query = query.filter(AuditLogEntry.action_type == action_type)
    if start_date:
        query = query.filter(AuditLogEntry.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLogEntry.timestamp <= end_date)
        
    query = query.order_by(AuditLogEntry.timestamp.desc())
    return query.offset(skip).limit(limit).all()

@router.get("/patient/{id}", response_model=List[AuditLogResponse])
def get_patient_audit_logs(
    id: str,
    skip: int = 0,
    limit: int = Query(100, le=1000),
    db: Session = Depends(get_db)
):
    """
    Full reconstruction of audit logs for one patient.
    """
    query = db.query(AuditLogEntry).filter(
        AuditLogEntry.target_entity == f"patient:{id}"
    )
    query = query.order_by(AuditLogEntry.timestamp.desc())
    return query.offset(skip).limit(limit).all()

# Intentionally omitting PATCH and DELETE routes to ensure the audit log is append-only.
