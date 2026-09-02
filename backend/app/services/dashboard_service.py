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
        query = query.filter(Visit.discharge_date >= start_dt)
    if end_dt:
        query = query.filter(Visit.admission_date < (end_dt + timedelta(days=1)))
    
    active_count = query.count()
    capacity = 50 if department else 200
    rate = min((active_count / capacity) * 100.0, 100.0) if capacity else 0.0
    
    return {
        "key": "occupancy",
        "label": "Occupancy",
        "value": round(rate, 1),
        "unit": "%",
        "chart": [{"label": "Occupied", "value": active_count}, {"label": "Available", "value": capacity - active_count}],
        "series": [],
        "available": True,
    }

def get_average_stay_metric(db: Session, department: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
    query = (
        db.query(Visit)
        .join(Document, Visit.document_id == Document.document_id)
        .filter(Document.status == DocumentStatus.COMMITTED.value)
        .filter(Visit.admission_date.isnot(None))
        .filter(Visit.discharge_date.isnot(None))
    )
    if department:
        query = query.filter(Visit.department == department)
    start_dt = _coerce_date(start_date)
    end_dt = _coerce_date(end_date)
    if start_dt:
        query = query.filter(Visit.visit_date >= start_dt)
    if end_dt:
        query = query.filter(Visit.visit_date < (end_dt + timedelta(days=1)))
    
    visits = query.all()
    if not visits:
        return {
            "key": "average_stay",
            "label": "Average Stay",
            "value": 0,
            "unit": "days",
            "chart": [],
            "series": [],
            "available": True,
        }
    
    total_days = sum(max((v.discharge_date - v.admission_date).days, 1) for v in visits)
    avg_stay = total_days / len(visits)
    
    return {
        "key": "average_stay",
        "label": "Average Stay",
        "value": round(avg_stay, 1),
        "unit": "days",
        "chart": [],
        "series": [],
        "available": True,
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
