"""Tool-calling natural-language report generation.

The model is deliberately constrained to two tools.  It can resolve a request
into filters and choose a chart, but all data access and rendering happen in
this module against committed canonical records.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.clinical_entities import Diagnosis, Medication, LabResult
from app.models.document import Document, DocumentStatus
from app.models.extracted_field import ExtractedField
from app.models.visit import Visit
from app.services.dashboard_service import _coerce_date

try:
    from app.config import settings
except ModuleNotFoundError:  # pragma: no cover - useful for isolated service tests
    class _Settings:
        AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama")
        OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
        OLLAMA_TIMEOUT = int(os.getenv("OLLAMA_TIMEOUT", "120"))
        GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

    settings = _Settings()


ALLOWED_CHART_TYPES = {"bar", "line", "pie"}
ALLOWED_GROUPINGS = {"diagnosis", "medication", "department", "month", "date"}


class ReportParseError(ValueError):
    """Raised when a request cannot be resolved to safe clinical filters."""


def _quarter_range(today: date) -> tuple[str, str]:
    start_month = ((today.month - 1) // 3) * 3 + 1
    start = date(today.year, start_month, 1)
    next_quarter = date(today.year + (start_month == 10), ((start_month + 2) % 12) + 1, 1)
    return start.isoformat(), (next_quarter - timedelta(days=1)).isoformat()


def _fallback_resolution(request: str) -> dict[str, Any]:
    """Safe availability fallback when the configured model is unavailable."""
    text = request.lower()
    filters: dict[str, Any] = {}
    diagnosis_match = re.search(r"(?:diagnos(?:is|es)|patients? with|for)\s+([a-z][a-z -]{2,40}?)(?:\s+(?:this|last|by|in)\b|$)", text)
    if diagnosis_match:
        filters["diagnosis_contains"] = diagnosis_match.group(1).strip()
    else:
        for term in ("diabetes", "diabetic", "hypertension", "asthma", "copd", "cancer"):
            if term in text:
                filters["diagnosis_contains"] = "diabetes" if term == "diabetic" else term
                break
    for department in ("cardiology", "neurology", "emergency", "orthopedics"):
        if department in text:
            filters["department"] = department.title()
            break
    if "this quarter" in text or "current quarter" in text:
        filters["date_from"], filters["date_to"] = _quarter_range(date.today())
    elif "last 30 days" in text:
        filters["date_from"] = (date.today() - timedelta(days=30)).isoformat()
        filters["date_to"] = date.today().isoformat()
    if not filters and not ("this quarter" in text or "current quarter" in text or "last 30 days" in text):
        return {}
    return {"filters": filters, "chart_type": "bar"}


def _extract_json(raw: str) -> dict[str, Any] | None:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None
    if not isinstance(value, dict):
        return None
    # Accept the exact tool-call envelope and a compact JSON response for
    # providers that do not expose native tool calls.
    calls = value.get("tool_calls") or []
    for call in calls:
        if call.get("name") == "run_structured_query":
            value["filters"] = call.get("arguments", {}).get("filters", call.get("arguments", {}))
        elif call.get("name") == "render_chart":
            value["chart_type"] = call.get("arguments", {}).get("chart_type")
    return value


def _call_report_llm(request: str) -> dict[str, Any] | None:
    prompt = f"""You are a read-only clinical report filter parser.
Return JSON only in this shape: {{"filters": {{...}}}}.
Do not return SQL, code, chart types, tool calls, or any fields outside the allowed filter keys.
Allowed filter keys: diagnosis_contains, icd10_code, snomed_code, medication_contains, rxnorm_code, loinc_code, department, date_from, date_to.
Use only real clinical columns. Dates must be YYYY-MM-DD. Resolve relative dates using today's date: {date.today().isoformat()}.
Request: {request}"""
    if os.getenv("REPORT_LLM_ENABLED", "1").lower() not in {"1", "true", "yes"}:
        return None
    try:
        if str(settings.AI_PROVIDER).lower() == "gemini" and settings.GEMINI_API_KEY:
            from google import genai
            response = genai.Client(api_key=settings.GEMINI_API_KEY).models.generate_content(
                model="gemini-3.5-flash", contents=prompt
            )
            return _extract_json(response.text or "")
        model = os.getenv("REPORT_LLM_MODEL", settings.OLLAMA_MODEL)
        payload = json.dumps({"model": model, "stream": False, "prompt": prompt, "format": "json", "options": {"temperature": 0}}).encode()
        req = urllib.request.Request(os.getenv("REPORT_LLM_URL", "http://localhost:11434/api/generate"), data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=min(3, settings.OLLAMA_TIMEOUT)) as response:
            return _extract_json(json.loads(response.read().decode()).get("response", ""))
    except Exception:
        return None


def resolve_report_request(request: str) -> dict[str, Any]:
    llm_result = _call_report_llm(request)
    result = llm_result if llm_result is not None else _fallback_resolution(request)
    if not result:
        raise ReportParseError("I couldn't identify safe clinical filters from that request. Please rephrase it with a diagnosis, medication, department, or date range.")
    raw_filters = result.get("filters") if isinstance(result.get("filters"), dict) else {}
    allowed = {"diagnosis_contains", "icd10_code", "snomed_code", "medication_contains", "rxnorm_code", "loinc_code", "department", "date_from", "date_to"}
    filters = {}
    for key, value in raw_filters.items():
        if key not in allowed or value in (None, ""):
            continue
        if not isinstance(value, str) or len(value) > 255:
            raise ReportParseError("I couldn't validate the filters in that request. Please rephrase it using plain clinical terms and dates.")
        if key in {"date_from", "date_to"} and _coerce_date(value) is None:
            raise ReportParseError("I couldn't validate the requested date range. Please use dates such as 2026-07-01.")
        filters[key] = value.strip()
    if not filters:
        raise ReportParseError("I couldn't identify safe clinical filters from that request. Please rephrase it with a diagnosis, medication, department, or date range.")
    return {"filters": filters}


def parse_nl_request(nl_query: str) -> dict[str, Any]:
    """Resolve and validate only fields that are safe for structured querying."""
    return resolve_report_request(nl_query)


def run_structured_query(db: Session, filters: dict[str, Any]) -> list[dict[str, Any]]:
    """The only data-access tool exposed to the report agent."""
    grouping = filters.get("group_by", "department")
    base = db.query(Visit).join(Document, Visit.document_id == Document.document_id).filter(Document.status == DocumentStatus.COMMITTED.value)
    if filters.get("department"):
        base = base.filter(Visit.department == filters["department"])
    if _coerce_date(filters.get("date_from")):
        base = base.filter(Visit.visit_date >= _coerce_date(filters["date_from"]))
    if _coerce_date(filters.get("date_to")):
        base = base.filter(Visit.visit_date < _coerce_date(filters["date_to"]) + timedelta(days=1))

    if filters.get("diagnosis_contains") or filters.get("icd10_code") or filters.get("snomed_code") or grouping == "diagnosis":
        query = base.join(ExtractedField, ExtractedField.document_id == Visit.document_id).join(Diagnosis, Diagnosis.source_field_id == ExtractedField.field_id)
        if filters.get("diagnosis_contains"):
            query = query.filter(Diagnosis.raw_text.ilike(f"%{filters['diagnosis_contains']}%"))
        if filters.get("icd10_code"):
            query = query.filter(Diagnosis.icd10_code == filters["icd10_code"])
        if filters.get("snomed_code"):
            query = query.filter(Diagnosis.snomed_code == filters["snomed_code"])
        rows = query.with_entities(Diagnosis.raw_text.label("label"), func.count(func.distinct(Diagnosis.patient_id)).label("count")).filter(Diagnosis.raw_text.isnot(None)).group_by(Diagnosis.raw_text).order_by(func.count(func.distinct(Diagnosis.patient_id)).desc()).all()
        return [{"label": row.label, "count": int(row.count)} for row in rows]

    if filters.get("medication_contains") or filters.get("rxnorm_code") or grouping == "medication":
        query = base.join(ExtractedField, ExtractedField.document_id == Visit.document_id).join(Medication, Medication.source_field_id == ExtractedField.field_id)
        if filters.get("medication_contains"):
            query = query.filter(Medication.raw_text.ilike(f"%{filters['medication_contains']}%"))
        if filters.get("rxnorm_code"):
            query = query.filter(Medication.rxnorm_code == filters["rxnorm_code"])
        rows = query.with_entities(Medication.raw_text.label("label"), func.count(func.distinct(Medication.patient_id)).label("count")).filter(Medication.raw_text.isnot(None)).group_by(Medication.raw_text).order_by(func.count(func.distinct(Medication.patient_id)).desc()).all()
        return [{"label": row.label, "count": int(row.count)} for row in rows]
        
    if filters.get("loinc_code") or grouping == "lab_result":
        query = base.join(ExtractedField, ExtractedField.document_id == Visit.document_id).join(LabResult, LabResult.source_field_id == ExtractedField.field_id)
        if filters.get("loinc_code"):
            query = query.filter(LabResult.loinc_code == filters["loinc_code"])
        rows = query.with_entities(LabResult.test_name.label("label"), func.count(func.distinct(LabResult.patient_id)).label("count")).filter(LabResult.test_name.isnot(None)).group_by(LabResult.test_name).order_by(func.count(func.distinct(LabResult.patient_id)).desc()).all()
        return [{"label": row.label, "count": int(row.count)} for row in rows]

    if grouping in {"month", "date"}:
        expression = func.strftime("%Y-%m", Visit.visit_date) if grouping == "month" else func.strftime("%Y-%m-%d", Visit.visit_date)
        rows = base.with_entities(expression.label("label"), func.count(func.distinct(Visit.patient_id)).label("count")).filter(Visit.visit_date.isnot(None)).group_by(expression).order_by(expression).all()
    else:
        rows = base.with_entities(Visit.department.label("label"), func.count(func.distinct(Visit.patient_id)).label("count")).filter(Visit.department.isnot(None)).group_by(Visit.department).order_by(func.count(func.distinct(Visit.patient_id)).desc()).all()
    return [{"label": row.label, "count": int(row.count)} for row in rows]


def render_chart(data: list[dict[str, Any]], chart_type: str) -> dict[str, Any]:
    """The only presentation tool exposed to the report agent."""
    if chart_type not in ALLOWED_CHART_TYPES:
        chart_type = "bar"
    return {"type": chart_type, "labels": [row.get("label") for row in data], "values": [row.get("count", 0) for row in data]}


def choose_chart_type(data: list[dict[str, Any]]) -> str:
    """Select a chart from returned data shape, without another model call."""
    labels = [str(row.get("label", "")) for row in data]
    if labels and all(re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", label) for label in labels):
        return "line"
    if data and len(data) <= 8 and all("percentage" in row or "proportion" in row for row in data):
        return "pie"
    return "bar"


def generate_report(db: Session, request: str) -> dict[str, Any]:
    resolved = parse_nl_request(request)
    data = run_structured_query(db, resolved["filters"])
    chart_type = choose_chart_type(data)
    chart = render_chart(data, chart_type)
    return {"request": request, "filters": resolved["filters"], "chart_type": chart_type, "data": data, "chart": chart}
