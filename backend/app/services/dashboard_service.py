from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.clinical_entities import Diagnosis
from app.models.document import Document, DocumentStatus
from app.models.extracted_field import ExtractedField
from app.models.patient import Patient
from app.models.visit import Visit


def _coerce_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _base_visit_query(db: Session, department: Optional[str], start_date: Optional[str], end_date: Optional[str]):
    query = (
        db.query(Visit)
        .join(Document, Visit.document_id == Document.document_id)
        .filter(Document.status == DocumentStatus.COMMITTED.value)
    )
    if department:
        query = query.filter(Visit.department == department)
    start_dt = _coerce_date(start_date)
    end_dt = _coerce_date(end_date)
    if start_dt:
        query = query.filter(Visit.visit_date >= start_dt)
    if end_dt:
        query = query.filter(Visit.visit_date < (end_dt + timedelta(days=1)))
    return query


def get_admissions_metric(db: Session, department: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
    query = _base_visit_query(db, department, start_date, end_date)
    total = query.filter(Visit.visit_date.isnot(None)).count()
    rows = query.filter(Visit.visit_date.isnot(None)).order_by(Visit.visit_date).all()
    chart_rows = [{"date": item.visit_date.date().isoformat(), "value": 1} for item in rows]
    return {
        "key": "admissions",
        "label": "Admissions",
        "value": total,
        "unit": "visits",
        "chart": chart_rows,
        "series": chart_rows,
        "available": True,
    }


def get_occupancy_metric(db: Session, department: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
    return {
        "key": "occupancy",
        "label": "Occupancy",
        "value": None,
        "unit": "%",
        "chart": [],
        "series": [],
        "available": False,
        "note": "Occupancy requires an admission/discharge date schema; none exists in the current Visit model.",
    }


def get_disease_distribution_metric(db: Session, department: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
    query = (
        db.query(Diagnosis.raw_text, func.count(Diagnosis.id).label("count"))
        .join(ExtractedField, Diagnosis.source_field_id == ExtractedField.field_id)
        .join(Document, ExtractedField.document_id == Document.document_id)
        .join(Visit, Visit.document_id == Document.document_id)
        .filter(Diagnosis.raw_text.isnot(None))
        .filter(Document.status == DocumentStatus.COMMITTED.value)
    )
    if department:
        query = query.filter(Visit.department == department)
    start_dt = _coerce_date(start_date)
    end_dt = _coerce_date(end_date)
    if start_dt:
        query = query.filter(Visit.visit_date >= start_dt)
    if end_dt:
        query = query.filter(Visit.visit_date < (end_dt + timedelta(days=1)))
    query = query.group_by(Diagnosis.raw_text).order_by(func.count(Diagnosis.id).desc())
    rows = query.all()
    series = [{"name": raw_text, "count": int(count)} for raw_text, count in rows]
    return {
        "key": "disease_distribution",
        "label": "Disease Distribution",
        "value": series[0]["count"] if series else 0,
        "unit": "patients",
        "chart": series,
        "series": series,
        "available": True,
    }


def get_readmission_rate_metric(db: Session, department: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
    visit_query = (
        db.query(Visit.patient_id, Visit.visit_date, Visit.department)
        .join(Document, Visit.document_id == Document.document_id)
        .filter(Document.status == DocumentStatus.COMMITTED.value)
    )
    if department:
        visit_query = visit_query.filter(Visit.department == department)
    start_dt = _coerce_date(start_date)
    end_dt = _coerce_date(end_date)
    if start_dt:
        visit_query = visit_query.filter(Visit.visit_date >= start_dt)
    if end_dt:
        visit_query = visit_query.filter(Visit.visit_date < (end_dt + timedelta(days=1)))
    visits = visit_query.order_by(Visit.patient_id, Visit.visit_date).all()
    patient_counts: Dict[str, int] = {}
    for patient_id, _, _ in visits:
        if not patient_id:
            continue
        patient_counts.setdefault(patient_id, 0)
        patient_counts[patient_id] += 1

    repeat_visits = sum(count - 1 for count in patient_counts.values() if count > 1)
    total_visits = len(visits)
    rate = (repeat_visits / total_visits * 100.0) if total_visits else 0.0
    chart = [{"label": "Repeat visits", "value": repeat_visits}, {"label": "Unique visits", "value": total_visits - repeat_visits}]
    return {
        "key": "readmission_rate",
        "label": "Readmission Rate",
        "value": round(rate, 2),
        "unit": "%",
        "chart": chart,
        "series": chart,
        "available": True,
    }


def get_average_stay_metric(db: Session, department: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
    return {
        "key": "average_stay",
        "label": "Average Stay",
        "value": None,
        "unit": "days",
        "chart": [],
        "series": [],
        "available": False,
        "note": "Average length of stay requires admission/discharge dates in the Visit table; the current schema has no such columns.",
    }


def get_department_dashboard(db: Session, department: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
    metrics = [
        get_admissions_metric(db, department, start_date, end_date),
        get_occupancy_metric(db, department, start_date, end_date),
        get_disease_distribution_metric(db, department, start_date, end_date),
        get_readmission_rate_metric(db, department, start_date, end_date),
        get_average_stay_metric(db, department, start_date, end_date),
    ]
    return {
        "department": department,
        "filters": {"department": department, "start_date": start_date, "end_date": end_date},
        "metrics": metrics,
    }


def get_hospital_dashboard(db: Session, start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
    metrics = [
        get_admissions_metric(db, None, start_date, end_date),
        get_occupancy_metric(db, None, start_date, end_date),
        get_disease_distribution_metric(db, None, start_date, end_date),
        get_readmission_rate_metric(db, None, start_date, end_date),
        get_average_stay_metric(db, None, start_date, end_date),
    ]
    return {
        "hospital": "main",
        "filters": {"department": None, "start_date": start_date, "end_date": end_date},
        "metrics": metrics,
    }
