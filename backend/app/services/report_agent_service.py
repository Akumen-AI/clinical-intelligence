"""Public report-agent service API.

The implementation remains compatible with the earlier service module while
exposing the agreed names used by the report API and tests.
"""

from app.services.nl_report_service import (
    ReportParseError,
    choose_chart_type as _choose_chart_type,
    parse_nl_request as _parse_nl_request,
    render_chart as _render_chart,
    run_structured_query as _run_structured_query,
)


def parse_nl_request(nl_query: str) -> dict:
    return _parse_nl_request(nl_query)


def run_structured_query(db, filters: dict, current_user=None) -> list[dict]:
    return _run_structured_query(db, filters, current_user)


def choose_chart_type(data: list[dict]) -> str:
    return _choose_chart_type(data)


def render_chart(data: list[dict], chart_type: str) -> dict:
    return _render_chart(data, chart_type)


__all__ = ["ReportParseError", "parse_nl_request", "run_structured_query", "choose_chart_type", "render_chart"]
