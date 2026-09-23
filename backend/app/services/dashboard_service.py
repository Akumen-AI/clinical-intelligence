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
        raise ValueError(f"Invalid date format: {value}")


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
    """
    Metric: Admissions
    Population: All recorded visits with a valid visit_date.
    Inclusion Rules: Visit falls within [start_date, end_date] and belongs to the specified department (if any).
    Exclusion Rules: Visits with null visit_date.
    Numerator: Count of included visits.
    Denominator: N/A
    Time Window: [start_date, end_date]
    Grouping: By date (for the chart).
    Source Tables: Visit, Document.
    Known Limitations: Treats every visit row as an admission; may overcount if outpatient visits are mixed with inpatient admissions.
    """
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
    """
    Metric: Occupancy
    Population: Inpatients currently occupying a bed at the end of the time window (or now).
    Inclusion Rules: admission_date <= target_date AND (discharge_date IS NULL OR discharge_date > target_date).
    Exclusion Rules: Outpatient visits lacking an admission_date.
    Numerator: Active admissions at the end of the window.
    Denominator: Configured or assumed hospital/department capacity.
    Time Window: target_date is end_date (or today if not provided).
    Grouping: N/A
    Source Tables: Visit, Document.
    Known Limitations: Capacity is hardcoded as a demo metric (200 hospital-wide, 50 per department).
    """
    query = (
        db.query(Visit)
        .join(Document, Visit.document_id == Document.document_id)
        .filter(Document.status == DocumentStatus.COMMITTED.value)
        .filter(Visit.admission_date.isnot(None))
    )
    if department:
        query = query.filter(Visit.department == department)
    
    target_dt = _coerce_date(end_date) or datetime.utcnow()
    query = query.filter(Visit.admission_date <= target_dt)
    query = query.filter((Visit.discharge_date.is_(None)) | (Visit.discharge_date > target_dt))
    
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

def get_disease_distribution_metric(db: Session, department: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
    """
    Metric: Disease Distribution
    Population: Diagnoses recorded in committed documents within the time window.
    Inclusion Rules: Visit falls within [start_date, end_date] and department.
    Exclusion Rules: Uncommitted documents, null raw_text.
    Numerator: Distinct count of patients per diagnosis raw_text.
    Denominator: N/A
    Time Window: [start_date, end_date] based on visit_date.
    Grouping: By diagnosis raw_text.
    Source Tables: Diagnosis, ExtractedField, Document, Visit.
    Known Limitations: Groups by raw_text rather than normalized code, potentially fragmenting identical conditions.
    """
    query = (
        db.query(Diagnosis.raw_text, func.count(func.distinct(Diagnosis.patient_id)).label("count"))
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
    query = query.group_by(Diagnosis.raw_text).order_by(func.count(func.distinct(Diagnosis.patient_id)).desc())
    rows = query.all()
    series = [{"name": raw_text, "count": int(count)} for raw_text, count in rows]
    return {
        "key": "disease_distribution",
        "label": "Disease Distribution",
        "value": sum(s["count"] for s in series),
        "unit": "diagnoses",
        "chart": series,
        "series": series,
        "available": True,
    }


def get_readmission_rate_metric(db: Session, department: Optional[str], start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Any]:
    """
    Metric: Readmission Rate (30-day)
    Population: Patients discharged within the time window.
    Inclusion Rules: Visit discharge_date falls within [start_date, end_date] and department.
    Exclusion Rules: Visits with no discharge_date.
    Numerator: Discharges that were followed by an admission within 30 days.
    Denominator: Total discharges in the window.
    Time Window: [start_date, end_date] based on discharge_date.
    Grouping: N/A
    Source Tables: Visit, Document.
    Known Limitations: A simplistic demo implementation mapping readmissions over any department if the first discharge was in the target department.
    """
    discharge_query = (
        db.query(Visit)
        .join(Document, Visit.document_id == Document.document_id)
        .filter(Document.status == DocumentStatus.COMMITTED.value)
        .filter(Visit.discharge_date.isnot(None))
    )
    if department:
        discharge_query = discharge_query.filter(Visit.department == department)
    start_dt = _coerce_date(start_date)
    end_dt = _coerce_date(end_date)
    if start_dt:
        discharge_query = discharge_query.filter(Visit.discharge_date >= start_dt)
    if end_dt:
        discharge_query = discharge_query.filter(Visit.discharge_date < (end_dt + timedelta(days=1)))
    
    discharges = discharge_query.with_entities(Visit.visit_id, Visit.patient_id, Visit.discharge_date).all()
    
    total_discharges = len(discharges)
    readmissions = 0
    
    if total_discharges > 0:
        patient_ids = list({d.patient_id for d in discharges if d.patient_id})
        
        # Fetch all admissions for these patients in one query
        from collections import defaultdict
        admissions_by_patient = defaultdict(list)
        
        if patient_ids:
            all_admissions = db.query(Visit.patient_id, Visit.visit_id, Visit.admission_date).filter(
                Visit.patient_id.in_(patient_ids),
                Visit.admission_date.isnot(None)
            ).all()
            
            for p_id, v_id, a_date in all_admissions:
                admissions_by_patient[p_id].append((v_id, a_date))
        
        for d in discharges:
            if not d.patient_id:
                continue
            
            for v_id, a_date in admissions_by_patient.get(d.patient_id, []):
                if v_id != d.visit_id and d.discharge_date <= a_date <= (d.discharge_date + timedelta(days=30)):
                    readmissions += 1
                    break

    rate = (readmissions / total_discharges * 100.0) if total_discharges else 0.0
    chart = [{"label": "30-day Readmissions", "value": readmissions}, {"label": "No Readmission", "value": total_discharges - readmissions}]
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
    """
    Metric: Average Length of Stay
    Population: Discharged inpatient visits.
    Inclusion Rules: Visit discharge_date falls within [start_date, end_date] and department. admission_date and discharge_date must be present.
    Exclusion Rules: Active admissions (not yet discharged).
    Numerator: Sum of days between admission and discharge. (Min 1 day).
    Denominator: Total count of discharges.
    Time Window: [start_date, end_date] based on discharge_date.
    Grouping: N/A
    Source Tables: Visit, Document.
    Known Limitations: Treats same-day discharges as 1 day instead of 0 or fractional days.
    """
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
        query = query.filter(Visit.discharge_date >= start_dt)
    if end_dt:
        query = query.filter(Visit.discharge_date < (end_dt + timedelta(days=1)))
    
    visits = query.with_entities(Visit.admission_date, Visit.discharge_date).all()
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
    
    total_days = sum(max((discharge - admission).days, 1) for admission, discharge in visits)
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
