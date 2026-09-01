from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import database
from app.core.security import create_access_token
from app.main import app
from app.models.clinical_entities import Diagnosis
from app.models.document import Document, DocumentStatus
from app.models.extracted_field import ExtractedField
from app.models.patient import Patient
from app.models.visit import Visit


@pytest.fixture
def dashboard_seed():
    db = database.SessionLocal()
    try:
        patient_1 = Patient(
            patient_id="p-dashboard-1",
            patient_number="MRN-101",
            name="Alice Patient",
            dob="1980-01-01",
            sex="F",
        )
        patient_2 = Patient(
            patient_id="p-dashboard-2",
            patient_number="MRN-202",
            name="Bob Patient",
            dob="1975-02-02",
            sex="M",
        )
        db.add_all([patient_1, patient_2])

        doc_1 = Document(
            document_id="doc-dashboard-1",
            filename="cardiology-1.pdf",
            raw_uri="uploads/cardio-1.pdf",
            filetype="pdf",
            status=DocumentStatus.COMMITTED.value,
            uploaded_at=datetime(2026, 2, 1, tzinfo=timezone.utc),
            document_type="visit_summary",
            patient_id="p-dashboard-1",
        )
        doc_2 = Document(
            document_id="doc-dashboard-2",
            filename="cardiology-2.pdf",
            raw_uri="uploads/cardio-2.pdf",
            filetype="pdf",
            status=DocumentStatus.COMMITTED.value,
            uploaded_at=datetime(2026, 2, 14, tzinfo=timezone.utc),
            document_type="visit_summary",
            patient_id="p-dashboard-1",
        )
        doc_3 = Document(
            document_id="doc-dashboard-3",
            filename="neurology-1.pdf",
            raw_uri="uploads/neuro-1.pdf",
            filetype="pdf",
            status=DocumentStatus.COMMITTED.value,
            uploaded_at=datetime(2026, 2, 12, tzinfo=timezone.utc),
            document_type="visit_summary",
            patient_id="p-dashboard-2",
        )
        db.add_all([doc_1, doc_2, doc_3])

        field_1 = ExtractedField(field_id="ef-dashboard-1", document_id="doc-dashboard-1", field_name="diagnoses", raw_value={"text": "Hypertension"}, confidence_score=1.0)
        field_2 = ExtractedField(field_id="ef-dashboard-2", document_id="doc-dashboard-2", field_name="diagnoses", raw_value={"text": "Hypertension"}, confidence_score=1.0)
        field_3 = ExtractedField(field_id="ef-dashboard-3", document_id="doc-dashboard-3", field_name="diagnoses", raw_value={"text": "Stroke"}, confidence_score=1.0)
        db.add_all([field_1, field_2, field_3])

        db.add_all([
            Diagnosis(id="diag-dashboard-1", patient_id="p-dashboard-1", source_field_id="ef-dashboard-1", raw_text="Hypertension"),
            Diagnosis(id="diag-dashboard-2", patient_id="p-dashboard-1", source_field_id="ef-dashboard-2", raw_text="Hypertension"),
            Diagnosis(id="diag-dashboard-3", patient_id="p-dashboard-2", source_field_id="ef-dashboard-3", raw_text="Stroke"),
        ])

        db.add_all([
            Visit(visit_id="visit-dashboard-1", patient_id="p-dashboard-1", document_id="doc-dashboard-1", visit_date=datetime(2026, 2, 1, tzinfo=timezone.utc), department="Cardiology"),
            Visit(visit_id="visit-dashboard-2", patient_id="p-dashboard-1", document_id="doc-dashboard-2", visit_date=datetime(2026, 2, 14, tzinfo=timezone.utc), department="Cardiology"),
            Visit(visit_id="visit-dashboard-3", patient_id="p-dashboard-2", document_id="doc-dashboard-3", visit_date=datetime(2026, 2, 12, tzinfo=timezone.utc), department="Neurology"),
        ])

        db.commit()
        yield
    finally:
        db.close()


def test_dashboard_department_metrics_are_live_and_filterable(dashboard_seed):
    token = create_access_token({"sub": "00000000-0000-0000-0000-000000000111", "role": "department_head", "email": "head@demo.com"})
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})

    response = client.get(
        "/api/v1/dashboards/department",
        params={"department": "Cardiology", "start_date": "2026-02-01", "end_date": "2026-02-28"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["department"] == "Cardiology"
    assert payload["filters"]["start_date"] == "2026-02-01"
    assert payload["filters"]["end_date"] == "2026-02-28"
    assert len(payload["metrics"]) >= 4

    admissions = next(item for item in payload["metrics"] if item["key"] == "admissions")
    disease = next(item for item in payload["metrics"] if item["key"] == "disease_distribution")
    readmission = next(item for item in payload["metrics"] if item["key"] == "readmission_rate")

    assert admissions["value"] == 2
    assert disease["series"][0]["count"] == 2
    assert readmission["value"] == 50.0

    hospital_response = client.get("/api/v1/dashboards/hospital", params={"start_date": "2026-02-01", "end_date": "2026-02-28"})
    assert hospital_response.status_code == 200, hospital_response.text
    assert hospital_response.json()["metrics"][0]["key"] == "admissions"


@pytest.mark.parametrize("role", ["doctor", "it", "compliance"])
def test_dashboard_requires_admin_or_department_head(role):
    token = create_access_token({"sub": "00000000-0000-0000-0000-000000000222", "role": role, "email": "sample@example.com"})
    client = TestClient(app)
    client.headers.update({"Authorization": f"Bearer {token}"})

    response = client.get("/api/v1/dashboards/hospital")
    assert response.status_code == 403, response.text
