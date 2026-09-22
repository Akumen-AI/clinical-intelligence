from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import User, get_current_user
from app.database import get_db
from app.models.report_request import ReportRequest
from app.schemas.nl_report import NaturalLanguageReportRequest, NaturalLanguageReportResponse
from app.services.audit_service import write_entry
from app.services.report_agent_service import ReportParseError, choose_chart_type, parse_nl_request, render_chart, run_structured_query
from app.core.authorization import AuthorizationService

router = APIRouter(prefix="/reports", tags=["Natural Language Reports"])


def _persist_attempt(db: Session, current_user: User, payload: NaturalLanguageReportRequest, filters: dict, chart_type: str, action_type: str, detail: str) -> ReportRequest:
    record = ReportRequest(
        actor_user_id=current_user.id,
        nl_query=payload.nl_query,
        resolved_filters=filters,
        chart_type=chart_type,
    )
    db.add(record)
    db.flush()
    write_entry(
        db,
        actor_user_id=current_user.id,
        action_type=action_type,
        target_entity=f"report_request:{record.id}",
        rationale=f"nl_query={payload.nl_query}; resolved_filters={filters}; {detail}",
    )
    return record


@router.post("/generate", response_model=NaturalLanguageReportResponse)
def generate_report(
    payload: NaturalLanguageReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        resolved = parse_nl_request(payload.nl_query)
        filters = resolved.get("filters", {})
        
        AuthorizationService.assert_can_export_report(current_user, department=filters.get("department"))
        
        data = run_structured_query(db, filters)
        chart_type = choose_chart_type(data)
        chart = render_chart(data, chart_type)
        _persist_attempt(db, current_user, payload, filters, chart_type, "agent_report_generated", "Report generated successfully.")
        return {"chart": chart, "resolved_filters": filters, "chart_type": chart_type, "data": data}
    except ReportParseError as exc:
        _persist_attempt(db, current_user, payload, {}, "error", "agent_report_failed", str(exc))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        _persist_attempt(db, current_user, payload, {}, "error", "agent_report_failed", "Report generation failed.")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Unable to generate the report.") from exc
