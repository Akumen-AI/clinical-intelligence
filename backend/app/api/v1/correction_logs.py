import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app.core.security import User
from app.schemas.correction_log import (
    CorrectionLogCreate,
    CorrectionLogRead,
    ExportBatchResponse,
)
from app.services.correction_log_service import CorrectionLogService
from app.core.authorization import AuthorizationService, Operation

from app.core.rbac import check_rbac

router = APIRouter(
    prefix="/correction-logs",
    tags=["Correction Logs (Story 3.2 FR-12)"],
    dependencies=[Depends(check_rbac)]
)

@router.post(
    "/",
    response_model=CorrectionLogRead,
    status_code=status.HTTP_201_CREATED,
    summary="Log one correction",
)
def create_correction_log(
    payload: CorrectionLogCreate,
    db: Session = Depends(get_db),
    request: Request = None,
):
    current_user = request.state.user
    AuthorizationService.assert_can_access_document(db, current_user, str(payload.document_id), Operation.WRITE)
    
    service = CorrectionLogService()
    log = service.log_correction(
        db=db,
        payload=payload,
        reviewer_id=current_user.id,
        reviewer_role=current_user.role,
    )
    return log

@router.post(
    "/export/retraining",
    response_model=ExportBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger PHI-safe export",
)
def export_retraining_logs_post(
    request: Request,
    limit: int = Query(default=1000, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    AuthorizationService.assert_can_access_audit_logs(request.state.user)
    service = CorrectionLogService()
    return service.export_for_retraining(db, limit=limit, actor_user_id=request.state.user.id)

@router.get(
    "/export/retraining",
    response_model=ExportBatchResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger PHI-safe export (GET variant)",
)
def export_retraining_logs_get(
    request: Request,
    limit: int = Query(default=1000, ge=1, le=10000),
    db: Session = Depends(get_db),
):
    AuthorizationService.assert_can_access_audit_logs(request.state.user)
    service = CorrectionLogService()
    return service.export_for_retraining(db, limit=limit, actor_user_id=request.state.user.id)

@router.get(
    "/document/{document_id}",
    response_model=list[CorrectionLogRead],
    status_code=status.HTTP_200_OK,
    summary="Fetch all logs for a document",
)
def get_document_correction_logs(
    document_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    AuthorizationService.assert_can_access_document(db, request.state.user, str(document_id), Operation.READ)
    service = CorrectionLogService()
    return service.get_logs_for_document(db, document_id)

@router.get(
    "/{log_id}",
    response_model=CorrectionLogRead,
    status_code=status.HTTP_200_OK,
    summary="Fetch single log",
)
def get_correction_log(
    log_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    service = CorrectionLogService()
    log = service.get_log_by_id(db, log_id)
    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Correction log '{log_id}' not found",
        )
    AuthorizationService.assert_can_access_document(db, request.state.user, str(log.document_id), Operation.READ)
    return log
