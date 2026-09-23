from datetime import datetime, timezone
import uuid

import pytest
from fastapi.testclient import TestClient

from app import database
from app.core.security import create_access_token
from app.main import app
from app.models.audit_log import AuditLogEntry
from app.models.clinical_entities import Diagnosis
from app.models.document import Document, DocumentStatus
from app.models.extracted_field import ExtractedField
from app.models.patient import Patient
from app.models.report_request import ReportRequest
from app.models.visit import Visit
from app.services.report_agent_service import parse_nl_request, run_structured_query


def _client(role: str = "doctor", user_id: str | None = None) -> TestClient:
    token = create_access_token({
        "sub": user_id or str(uuid.uuid4()),
        "role": role,
        "email": f"{role}@test.clinic.org",
    })
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture
def report_seed(monkeypatch):
    monkeypatch.setenv("REPORT_LLM_ENABLED", "0")
    db = database.SessionLocal()
    patient_diabetes = Patient(patient_id="report-patient-diabetes", mrn="REPORT-1", name="Diabetes Patient")
    patient_hypertension = Patient(patient_id="report-patient-hypertension", mrn="REPORT-2", name="Hypertension Patient")
    patient_old = Patient(patient_id="report-patient-old", mrn="REPORT-3", name="Old Diabetes Patient")
    db.add_all([patient_diabetes, patient_hypertension, patient_old])

    documents = [
        Document(document_id="report-doc-diabetes", patient_id=patient_diabetes.patient_id, filename="diabetes.pdf", raw_uri="uploads/diabetes.pdf", filetype="pdf", status=DocumentStatus.COMMITTED.value),
        Document(document_id="report-doc-hypertension", patient_id=patient_hypertension.patient_id, filename="hypertension.pdf", raw_uri="uploads/hypertension.pdf", filetype="pdf", status=DocumentStatus.COMMITTED.value),
        Document(document_id="report-doc-old", patient_id=patient_old.patient_id, filename="old-diabetes.pdf", raw_uri="uploads/old-diabetes.pdf", filetype="pdf", status=DocumentStatus.COMMITTED.value),
    ]
    db.add_all(documents)
    db.add_all([
        ExtractedField(field_id="report-field-diabetes", document_id="report-doc-diabetes", field_name="diagnoses", raw_value={"text": "Type 2 diabetes"}, confidence_score=1.0),
        ExtractedField(field_id="report-field-hypertension", document_id="report-doc-hypertension", field_name="diagnoses", raw_value={"text": "Hypertension"}, confidence_score=1.0),
        ExtractedField(field_id="report-field-old", document_id="report-doc-old", field_name="diagnoses", raw_value={"text": "Type 2 diabetes"}, confidence_score=1.0),
    ])
    db.add_all([
        Diagnosis(id="report-diagnosis-diabetes", patient_id=patient_diabetes.patient_id, source_field_id="report-field-diabetes", raw_text="Type 2 diabetes"),
        Diagnosis(id="report-diagnosis-hypertension", patient_id=patient_hypertension.patient_id, source_field_id="report-field-hypertension", raw_text="Hypertension"),
        Diagnosis(id="report-diagnosis-old", patient_id=patient_old.patient_id, source_field_id="report-field-old", raw_text="Type 2 diabetes"),
    ])
    db.add_all([
        Visit(visit_id="report-visit-diabetes", patient_id=patient_diabetes.patient_id, document_id="report-doc-diabetes", visit_date=datetime(2026, 8, 10, tzinfo=timezone.utc), department="Endocrinology"),
        Visit(visit_id="report-visit-hypertension", patient_id=patient_hypertension.patient_id, document_id="report-doc-hypertension", visit_date=datetime(2026, 8, 11, tzinfo=timezone.utc), department="Cardiology"),
        Visit(visit_id="report-visit-old", patient_id=patient_old.patient_id, document_id="report-doc-old", visit_date=datetime(2026, 4, 10, tzinfo=timezone.utc), department="Endocrinology"),
    ])
    db.commit()
    db.close()
    yield


def test_known_query_resolves_filters_and_returns_only_matching_data(report_seed):
    resolved = parse_nl_request("diabetic patients this quarter")
    assert resolved["filters"] == {
        "diagnosis_contains": "diabetes",
        "date_from": "2026-07-01",
        "date_to": "2026-09-30",
    }

    db = database.SessionLocal()
    try:
        rows = run_structured_query(db, resolved["filters"])
    finally:
        db.close()
    assert rows == [{"label": "Type 2 diabetes", "count": 1}]


def test_api_response_includes_resolved_filters_and_chart_type(report_seed, client_as):
    response = client_as("hospital_admin").post("/api/v1/reports/generate", json={"nl_query": "diabetic patients this quarter"})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["resolved_filters"]["diagnosis_contains"] == "diabetes"
    assert payload["resolved_filters"]["date_from"] == "2026-07-01"
    assert payload["resolved_filters"]["date_to"] == "2026-09-30"
    assert payload["chart_type"] in {"bar", "line", "pie"}


def test_success_creates_report_request_and_audit_log(report_seed, client_as):
    actor_id = str(uuid.uuid4())
    response = client_as("hospital_admin").post("/api/v1/reports/generate", json={"nl_query": "diabetic patients this quarter"})
    assert response.status_code == 200, response.text

    db = database.SessionLocal()
    try:
        request = db.query(ReportRequest).filter(ReportRequest.nl_query == "diabetic patients this quarter").one()
        audit = db.query(AuditLogEntry).filter(AuditLogEntry.action_type == "agent_report_generated").one()
        assert request.nl_query == "diabetic patients this quarter"
        assert request.resolved_filters["diagnosis_contains"] == "diabetes"
        assert request.chart_type == response.json()["chart_type"]
        
        assert "diabetic patients this quarter" in audit.rationale
        assert "diagnosis_contains" in audit.rationale
    finally:
        db.close()


def test_failed_unparseable_call_creates_report_request_and_audit_log(monkeypatch, client_as):
    monkeypatch.setenv("REPORT_LLM_ENABLED", "0")
    actor_id = str(uuid.uuid4())
    response = client_as("hospital_admin").post("/api/v1/reports/generate", json={"nl_query": "tell me something random"})
    assert response.status_code == 422, response.text
    assert "rephrase" in response.json()["detail"].lower()

    db = database.SessionLocal()
    try:
        request = db.query(ReportRequest).filter(ReportRequest.nl_query == "tell me something random").one()
        audit = db.query(AuditLogEntry).filter(AuditLogEntry.action_type == "agent_report_failed").one()
        assert request.nl_query == "tell me something random"
        assert request.resolved_filters == {}
        assert request.chart_type == "error"
        
        assert "tell me something random" in audit.rationale
    finally:
        db.close()


def test_unauthorized_role_gets_403(report_seed):
    response = _client("nurse").post("/api/v1/reports/generate", json={"nl_query": "diabetic patients this quarter"})
    assert response.status_code == 403, response.text
