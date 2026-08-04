import uuid
import json
from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient

from app.models.document import Document, DocumentStatus
from app.models.extracted_field import ExtractedField
from app.schemas.extracted_field import ClinicalFieldsSchema, DocumentFieldsResponseSchema
from app.services.extraction.rule_based_extractor import RuleBasedFieldExtractor
from app.services.extraction.ollama_extractor import OllamaFieldExtractor
from app.services.extraction.gemini_extractor import GeminiFieldExtractor
from app.services.extraction.factory import get_field_extractor
from app.config import settings
from app.services.field_extraction_service import (
    extract_and_persist_fields,
    get_document_fields_response,
)
from tests.conftest import TestingSessionLocal


SAMPLE_PRESCRIPTION_TEXT = """
CITY GENERAL HOSPITAL - OUTPATIENT CLINIC
Patient Name: Jane Doe
DOB: 1985-04-12
Gender: Female
MRN: MRN-987654
Date: 2026-07-15
Prescribing Doctor: Dr. Robert Adams, MD
Department: Internal Medicine

Diagnosis:
- Essential Hypertension (I10)
- Type 2 Diabetes Mellitus (E11.9)

Rx / Medications:
1. Lisinopril 10mg once daily PO for 30 days
2. Metformin 500mg twice daily PO with meals for 90 days

Instructions:
Take medications as prescribed. Monitor blood pressure weekly.
Signature: Dr. Robert Adams
"""

SAMPLE_LAB_REPORT_TEXT = """
METROPOLITAN CLINICAL LABORATORY
Patient Name: John Smith
Patient ID: LAB-554433
Date: 2026-07-20
Ordering Physician: Dr. Emily Clark
Department: Pathology

COMPREHENSIVE METABOLIC & CBC PANEL
Hemoglobin: 14.5 g/dL (13.5 - 17.5) Normal
WBC: 11.8 x10^3/uL (4.5 - 11.0) High
Glucose: 145 mg/dL (70 - 99) High
Creatinine: 0.9 mg/dL (0.6 - 1.2) Normal
Sodium: 140 mmol/L (135 - 145) Normal
Potassium: 4.2 mmol/L (3.5 - 5.0) Normal
"""

SAMPLE_DISCHARGE_SUMMARY_TEXT = """
ST. JUDE MEDICAL CENTER - DISCHARGE SUMMARY
Patient Name: Eleanor Vance
DOB: 1962-11-03
Gender: Female
MRN: MRN-112233
Encounter Date: 2026-07-25
Physician: Dr. Marcus Welby
Department: Cardiology

Chief Complaint:
- Severe chest pain
- Shortness of breath

Vitals:
BP: 135/85 mmHg
HR: 78 bpm
Temp: 98.6 F
RR: 16 /min
SpO2: 98%
Weight: 68 kg
Height: 165 cm
BMI: 25.0

Diagnosis:
- Acute Coronary Syndrome
- Hyperlipidemia

Procedures:
- Coronary Angiography
- Drug-Eluting Stent Placement

Discharge Medications:
- Aspirin 81mg daily PO
- Atorvastatin 40mg at bedtime PO
- Clopidogrel 75mg daily PO
"""


def test_prescription_field_extraction():
    """Verify field extraction for Prescription document type."""
    extractor = RuleBasedFieldExtractor()
    result = extractor.extract(SAMPLE_PRESCRIPTION_TEXT, document_type="Prescription")

    fields = result.fields
    assert fields.patient_identifier is not None
    assert fields.patient_identifier.name == "Jane Doe"
    assert fields.patient_identifier.patient_id == "MRN-987654"
    assert fields.patient_identifier.dob == "1985-04-12"
    assert fields.patient_identifier.gender == "Female"

    assert fields.document_date == "2026-07-15"
    assert fields.ordering_physician is not None
    assert "Robert Adams" in fields.ordering_physician.name
    assert fields.ordering_physician.department == "Internal Medicine"

    assert fields.diagnosis is not None
    assert len(fields.diagnosis) >= 2
    assert any("Hypertension" in d.condition_name for d in fields.diagnosis)

    assert fields.medications is not None
    assert len(fields.medications) >= 2
    assert any("Lisinopril" in m.medication_name for m in fields.medications)

    # Acceptance Criterion 3: Missing fields MUST be explicitly None/null
    assert fields.vitals is None
    assert fields.lab_results is None
    assert fields.symptoms is None
    assert fields.procedures is None


def test_lab_report_field_extraction():
    """Verify field extraction for Lab Report document type."""
    extractor = RuleBasedFieldExtractor()
    result = extractor.extract(SAMPLE_LAB_REPORT_TEXT, document_type="Lab Report")

    fields = result.fields
    assert fields.patient_identifier is not None
    assert fields.patient_identifier.name == "John Smith"
    assert fields.patient_identifier.patient_id == "LAB-554433"

    assert fields.document_date == "2026-07-20"
    assert fields.ordering_physician is not None
    assert "Emily Clark" in fields.ordering_physician.name

    assert fields.lab_results is not None
    assert len(fields.lab_results) >= 4
    test_names = [l.test_name.lower() for l in fields.lab_results]
    assert any("hemoglobin" in n for n in test_names)
    assert any("glucose" in n for n in test_names)

    # Acceptance Criterion 3: Missing fields MUST be explicitly None/null
    assert fields.medications is None
    assert fields.vitals is None
    assert fields.diagnosis is None
    assert fields.symptoms is None
    assert fields.procedures is None


def test_discharge_summary_field_extraction():
    """Verify field extraction for Discharge Summary document type."""
    extractor = RuleBasedFieldExtractor()
    result = extractor.extract(SAMPLE_DISCHARGE_SUMMARY_TEXT, document_type="Discharge Summary")

    fields = result.fields
    assert fields.patient_identifier is not None
    assert fields.patient_identifier.name == "Eleanor Vance"

    assert fields.vitals is not None
    assert fields.vitals.blood_pressure == "135/85 mmHg"
    assert fields.vitals.heart_rate == "78 bpm"
    assert fields.vitals.temperature == "98.6 F"
    assert fields.vitals.spo2 == "98%"

    assert fields.diagnosis is not None
    assert len(fields.diagnosis) >= 1

    assert fields.medications is not None
    assert len(fields.medications) >= 2

    assert fields.symptoms is not None
    assert len(fields.symptoms) >= 1

    assert fields.procedures is not None
    assert len(fields.procedures) >= 1

    # Lab results was not in this text -> explicitly None
    assert fields.lab_results is None


def test_explicit_null_representation_in_schema():
    """
    Acceptance Criterion 3: Missing fields are represented explicitly (null), not omitted.
    """
    empty_fields = ClinicalFieldsSchema()
    dumped = empty_fields.model_dump()

    required_keys = [
        "patient_identifier",
        "document_date",
        "ordering_physician",
        "vitals",
        "diagnosis",
        "medications",
        "lab_results",
        "symptoms",
        "procedures",
    ]

    for key in required_keys:
        assert key in dumped
        assert dumped[key] is None


def test_ollama_extractor_mock(mocker):
    """Test Ollama extractor with mocked response."""
    sample_json = {
        "patient_identifier": {"name": "Test Patient", "patient_id": "P123", "dob": "1990-01-01", "gender": "Male"},
        "document_date": "2026-07-28",
        "ordering_physician": {"name": "Dr. Test", "npi_or_license": None, "department": None},
        "vitals": None,
        "diagnosis": [{"condition_name": "Asthma", "icd10_code": "J45", "notes": None}],
        "medications": [{"medication_name": "Albuterol", "dosage": "90mcg", "frequency": "PRN", "route": "Inhalation", "duration": None, "instructions": None}],
        "lab_results": None,
        "symptoms": None,
        "procedures": None,
    }
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": json.dumps(sample_json)}
    mocker.patch("requests.post", return_value=mock_response)

    extractor = OllamaFieldExtractor()
    result = extractor.extract("Sample prescription text")
    assert result.fields.patient_identifier.name == "Test Patient"
    assert result.fields.vitals is None
    assert result.fields.medications[0].medication_name == "Albuterol"


def test_gemini_extractor_mock(mocker):
    """Test Gemini extractor with mocked response."""
    sample_json = {
        "patient_identifier": {"name": "Gemini Patient", "patient_id": "GP-1", "dob": None, "gender": "Female"},
        "document_date": "2026-07-29",
        "ordering_physician": None,
        "vitals": None,
        "diagnosis": None,
        "medications": None,
        "lab_results": [{"test_name": "Hemoglobin", "value": "13.0", "unit": "g/dL", "reference_range": "12-16", "flag": "Normal"}],
        "symptoms": None,
        "procedures": None,
    }
    mock_client = MagicMock()
    mock_generate = MagicMock()
    mock_generate.text = json.dumps(sample_json)
    mock_client.models.generate_content.return_value = mock_generate
    mocker.patch("google.genai.Client", return_value=mock_client)

    extractor = GeminiFieldExtractor(api_key="mock_key")
    result = extractor.extract("Sample lab text")
    assert result.fields.patient_identifier.name == "Gemini Patient"
    assert result.fields.lab_results[0].test_name == "Hemoglobin"
    assert result.fields.medications is None


def test_get_document_fields_api(client, monkeypatch, tmp_path):
    """Test GET /api/v1/documents/{document_id}/fields endpoint."""
    dummy_file = tmp_path / "sample_doc.txt"
    dummy_file.write_text(SAMPLE_PRESCRIPTION_TEXT)

    doc_id = str(uuid.uuid4())
    db = TestingSessionLocal()
    try:
        doc = Document(
            document_id=doc_id,
            filename="prescription.pdf",
            raw_uri=str(dummy_file),
            filetype="application/pdf",
            status=DocumentStatus.CLASSIFIED.value,
            document_type="Prescription",
            classification_confidence=0.95,
        )
        db.add(doc)
        db.commit()

        monkeypatch.setattr(
            "app.services.field_extraction_service.extract_text",
            lambda uri, ft: SAMPLE_PRESCRIPTION_TEXT,
        )
        monkeypatch.setattr(
            "app.services.field_extraction_service.get_field_extractor",
            lambda: RuleBasedFieldExtractor(),
        )

        response = client.get(f"/api/v1/documents/{doc_id}/fields")
        assert response.status_code == 200
        data = response.json()

        assert data["document_id"] == doc_id
        assert data["document_type"] == "Prescription"
        assert "fields" in data
        assert data["fields"]["patient_identifier"]["name"] == "Jane Doe"
        assert data["fields"]["document_date"] == "2026-07-15"
        assert data["fields"]["vitals"] is None
        assert data["fields"]["lab_results"] is None

        assert "field_records" in data
        assert len(data["field_records"]) > 0
    finally:
        db.close()


def test_trigger_extract_fields_api(client, monkeypatch, tmp_path):
    """Test POST /api/v1/documents/{document_id}/extract endpoint."""
    dummy_file = tmp_path / "sample_lab.txt"
    dummy_file.write_text(SAMPLE_LAB_REPORT_TEXT)

    doc_id = str(uuid.uuid4())
    db = TestingSessionLocal()
    try:
        doc = Document(
            document_id=doc_id,
            filename="lab_report.pdf",
            raw_uri=str(dummy_file),
            filetype="application/pdf",
            status=DocumentStatus.CLASSIFIED.value,
            document_type="Lab Report",
            classification_confidence=0.96,
        )
        db.add(doc)
        db.commit()

        monkeypatch.setattr(
            "app.services.field_extraction_service.extract_text",
            lambda uri, ft: SAMPLE_LAB_REPORT_TEXT,
        )
        monkeypatch.setattr(
            "app.services.field_extraction_service.get_field_extractor",
            lambda: RuleBasedFieldExtractor(),
        )

        response = client.post(f"/api/v1/documents/{doc_id}/extract")
        assert response.status_code == 200
        data = response.json()

        assert data["document_id"] == doc_id
        assert data["fields"]["patient_identifier"]["name"] == "John Smith"
        assert data["fields"]["medications"] is None
        assert len(data["fields"]["lab_results"]) >= 4

        # Check DB status updated to extracted
        db.refresh(doc)
        assert doc.status == DocumentStatus.EXTRACTED.value
    finally:
        db.close()


def test_get_document_fields_404(client):
    """Test GET /api/v1/documents/{document_id}/fields with invalid UUID returns 404."""
    non_existent_id = str(uuid.uuid4())
    response = client.get(f"/api/v1/documents/{non_existent_id}/fields")
    assert response.status_code == 404
