import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.database import get_db
from app.dependencies.auth import get_current_user
from app.services import rag_service, context_panel_service
from app.core.compliance import enforce_ac3, ComplianceViolationError

router = APIRouter(prefix="/api/v1", tags=["compliance_endpoints"])


class RAGQueryRequest(BaseModel):
    patient_id: str
    query: str


@router.post("/rag/query")
async def rag_query(
    payload: RAGQueryRequest,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    try:
        answer = await rag_service.run_rag_chain(payload.patient_id, payload.query)
        answer = enforce_ac3(answer)
        return {"answer": answer, "patient_id": payload.patient_id}
    except ComplianceViolationError as e:
        raise HTTPException(
            status_code=422,
            detail=f"RAG answer rejected by AC-3 compliance check: {e.phrase}",
        )


@router.get("/context-panel/{patient_id}")
async def get_context_panel_route(
    patient_id: str,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    try:
        panel_data = await context_panel_service.get_context_panel(db, patient_id)
        if isinstance(panel_data, str):
            enforce_ac3(panel_data)
            return {"panel_text": panel_data}
        return panel_data
    except ComplianceViolationError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Context panel rejected by AC-3 compliance check: {e.phrase}",
        )
