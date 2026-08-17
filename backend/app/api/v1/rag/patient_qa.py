from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.models.user import User
from app.core.security import get_current_active_user
from app.services.rag.patient_rag_service import (
    PatientRagService,
    get_patient_rag_service,
    RagAnswer,
)
from app.services.rag.rbac_access_guard import AccessDeniedError

router = APIRouter(prefix="/api/v1/rag/patient", tags=["RAG Patient QA"])


class RagQueryRequest(BaseModel):
    question: str


@router.post("/{patient_id}/query", response_model=RagAnswer)
async def query_patient(
    patient_id: UUID,
    body: RagQueryRequest,
    current_user: User = Depends(get_current_active_user),
    rag_service: PatientRagService = Depends(get_patient_rag_service),
):
    try:
        answer = await rag_service.query(
            patient_id=patient_id,
            question=body.question,
            user=current_user,
        )
        return answer
    except AccessDeniedError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
