"""
Story 10.1 — Test suite for GET /api/v1/patients/{patient_id}/context-panel

Acceptance criteria enforced:
  AC-1  Panel is returned on the first GET of the patient profile endpoint.
  AC-2  Every item in the panel originates from a canonical DB row,
        not from a generated/inferred source.
  AC-3  No condition, diagnosis, ICD code, or diagnostic label appears
        anywhere in the JSON response even when Diagnosis rows exist in the DB.

23 test cases covering:
  - Happy-path data presence
  - Per-section data accuracy (medications, allergies, prior_results, history)
  - AC-3 isolation: Diagnosis rows in DB must NEVER surface in response
  - RBAC: 401 without token, 403 for department_head
  - Edge cases: unknown patient, empty canonical record
  - source field always equals "canonical_record"
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import create_access_token
from app.database import get_db
from app.models.patient import Patient
from app.models.document import Document, DocumentStatus
from app.models.extracted_field import ExtractedField, VerificationStatus
from app.models.canonical_patient_record import CanonicalPatientRecord
from app.models.clinical_entities import Medication, Diagnosis, LabResult
from tests.conftest import TestingSessionLocal


# ─────────────────────────── helpers ────────────────────────────────────────

def _make_token(role: str, patient_access: list[str] | None = None) -> str:
    payload: dict = {"sub": str(uuid.uuid4()), "role": role, "email": f"{role}@test.org"}
    if patient_access is not None:
        payload["patient_access"] = patient_access
    return create_access_token(payload)


def _client_for(role: str, patient_access: list[str] | None = None) -> TestClient:
    token = _make_token(role, patient_access)
    c = TestClient(app)
    c.headers.update({"Authorization": f"Bearer {token}"})
    return c


def _seed_patient(db) -> Patient:
    p = Patient(
        patient_id=str(uuid.uuid4()),
        patient_number=f"PT-{uuid.uuid4().hex[:6]}",
        mrn=f"MRN-{uuid.uuid4().hex[:6]}",
        name="Test Patient",
        dob="1980-01-01",
        sex="M",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _seed_document(db, patient_id: str) -> Document:
    doc = Document(
        document_id=str(uuid.uuid4()),
        patient_id=patient_id,
        filename="test.pdf",
        raw_uri="uploads/test.pdf",
        filetype="pdf",
        status=DocumentStatus.COMMITTED.value,
        document_type="Clinical Note",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def _seed_medication(db, patient_id: str, raw_text: str = "Metformin 500mg", rxnorm: str | None = "860975") -> Medication:
    ef = ExtractedField(
        field_id=str(uuid.uuid4()),
        document_id=_seed_document(db, patient_id).document_id,
        field_name="medications",
        raw_value=raw_text,
        confidence_score=0.95,
        verification_status=VerificationStatus.AUTO_PASSED,
    )
    db.add(ef)
    db.flush()
    m = Medication(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        source_field_id=ef.field_id,
        raw_text=raw_text,
        rxnorm_code=rxnorm,
    )
    db.add(m)
    db.commit()
    return m


def _seed_lab_result(db, patient_id: str, raw_text: str = "HbA1c 7.2%", loinc: str | None = "4548-4") -> LabResult:
    doc = _seed_document(db, patient_id)
    ef = ExtractedField(
        field_id=str(uuid.uuid4()),
        document_id=doc.document_id,
        field_name="lab_results",
        raw_value=raw_text,
        confidence_score=0.90,
        verification_status=VerificationStatus.AUTO_PASSED,
    )
    db.add(ef)
    db.flush()
    lr = LabResult(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        source_field_id=ef.field_id,
        raw_text=raw_text,
        loinc_code=loinc,
    )
    db.add(lr)
    db.commit()
    return lr


def _seed_allergy_canonical(db, patient_id: str, allergy_value) -> CanonicalPatientRecord:
    doc = _seed_document(db, patient_id)
    ef = ExtractedField(
        field_id=str(uuid.uuid4()),
        document_id=doc.document_id,
        field_name="allergies",
        raw_value=allergy_value,
        confidence_score=0.97,
        verification_status=VerificationStatus.HUMAN_VERIFIED,
    )
    db.add(ef)
    db.flush()
    cr = CanonicalPatientRecord(
        document_id=doc.document_id,
        field_name="allergies",
        value=allergy_value,
        source_field_id=ef.field_id,
    )
    db.add(cr)
    db.commit()
    return cr


def _seed_history_canonical(db, patient_id: str, history_value: str) -> CanonicalPatientRecord:
    doc = _seed_document(db, patient_id)
    ef = ExtractedField(
        field_id=str(uuid.uuid4()),
        document_id=doc.document_id,
        field_name="medical_history",
        raw_value=history_value,
        confidence_score=0.88,
        verification_status=VerificationStatus.AUTO_PASSED,
    )
    db.add(ef)
    db.flush()
    cr = CanonicalPatientRecord(
        document_id=doc.document_id,
        field_name="medical_history",
        value=history_value,
        source_field_id=ef.field_id,
    )
    db.add(cr)
    db.commit()
    return cr


def _seed_diagnosis(db, patient_id: str, raw_text: str = "Type 2 Diabetes", icd10: str = "E11") -> Diagnosis:
    """Seeds a Diagnosis row that MUST NOT appear in the context panel (AC-3)."""
    doc = _seed_document(db, patient_id)
    ef = ExtractedField(
        field_id=str(uuid.uuid4()),
        document_id=doc.document_id,
        field_name="diagnoses",
        raw_value=raw_text,
        confidence_score=0.92,
        verification_status=VerificationStatus.AUTO_PASSED,
    )
    db.add(ef)
    db.flush()
    d = Diagnosis(
        id=str(uuid.uuid4()),
        patient_id=patient_id,
        source_field_id=ef.field_id,
        raw_text=raw_text,
        icd10_code=icd10,
    )
    db.add(d)
    db.commit()
    return d


# ─────────────────────────── fixtures ───────────────────────────────────────

@pytest.fixture
def admin_client():
    return _client_for("hospital_admin")


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─────────────────────────── tests ──────────────────────────────────────────

class TestContextPanelHappyPath:

    def test_returns_200_for_known_patient(self, admin_client, db_session):
        """AC-1: endpoint responds 200 for a valid patient."""
        p = _seed_patient(db_session)
        resp = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel")
        assert resp.status_code == 200

    def test_response_has_required_top_level_keys(self, admin_client, db_session):
        """AC-1/AC-2: response shape includes all four data sections plus source."""
        p = _seed_patient(db_session)
        resp = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel")
        data = resp.json()
        assert "medications" in data
        assert "allergies" in data
        assert "prior_results" in data
        assert "history" in data
        assert "source" in data

    def test_source_field_is_canonical_record(self, admin_client, db_session):
        """AC-2: source field always equals 'canonical_record'."""
        p = _seed_patient(db_session)
        resp = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel")
        assert resp.json()["source"] == "canonical_record"

    def test_empty_patient_returns_empty_lists(self, admin_client, db_session):
        """AC-2: no data for empty patient → all sections are empty lists."""
        p = _seed_patient(db_session)
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        assert data["medications"] == []
        assert data["allergies"] == []
        assert data["prior_results"] == []
        assert data["history"] == []


class TestMedicationsSection:

    def test_seeded_medication_appears_in_panel(self, admin_client, db_session):
        """AC-2: medication seeded in DB shows up in panel."""
        p = _seed_patient(db_session)
        _seed_medication(db_session, p.patient_id, "Lisinopril 10mg", "29046")
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        raw_texts = [m["raw_text"] for m in data["medications"]]
        assert "Lisinopril 10mg" in raw_texts

    def test_medication_carries_rxnorm_code(self, admin_client, db_session):
        """AC-2: rxnorm_code is preserved in panel output."""
        p = _seed_patient(db_session)
        _seed_medication(db_session, p.patient_id, "Atorvastatin 20mg", "617310")
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        codes = [m.get("rxnorm_code") for m in data["medications"]]
        assert "617310" in codes

    def test_multiple_medications_all_returned(self, admin_client, db_session):
        """AC-2: all canonical medications for patient are returned."""
        p = _seed_patient(db_session)
        _seed_medication(db_session, p.patient_id, "Med A")
        _seed_medication(db_session, p.patient_id, "Med B")
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        assert len(data["medications"]) == 2


class TestAllergiesSection:

    def test_string_allergy_appears_in_panel(self, admin_client, db_session):
        """AC-2: string allergy from canonical record surfaces in panel."""
        p = _seed_patient(db_session)
        _seed_allergy_canonical(db_session, p.patient_id, "Penicillin")
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        assert "Penicillin" in data["allergies"]

    def test_list_allergy_expanded_in_panel(self, admin_client, db_session):
        """AC-2: list-valued allergy canonical record is expanded to individual strings."""
        p = _seed_patient(db_session)
        _seed_allergy_canonical(db_session, p.patient_id, ["Sulfa", "NSAIDs"])
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        assert "Sulfa" in data["allergies"]
        assert "NSAIDs" in data["allergies"]


class TestPriorResultsSection:

    def test_seeded_lab_result_appears_in_prior_results(self, admin_client, db_session):
        """AC-2: lab result seeded in DB appears under prior_results."""
        p = _seed_patient(db_session)
        _seed_lab_result(db_session, p.patient_id, "HbA1c 7.2%", "4548-4")
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        raw_texts = [r["raw_text"] for r in data["prior_results"]]
        assert "HbA1c 7.2%" in raw_texts

    def test_prior_result_carries_loinc_code(self, admin_client, db_session):
        """AC-2: loinc_code preserved in panel output."""
        p = _seed_patient(db_session)
        _seed_lab_result(db_session, p.patient_id, "WBC 6.5", "6690-2")
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        codes = [r.get("loinc_code") for r in data["prior_results"]]
        assert "6690-2" in codes


class TestHistorySection:

    def test_medical_history_surfaces_in_panel(self, admin_client, db_session):
        """AC-2: medical_history canonical record appears in history list."""
        p = _seed_patient(db_session)
        _seed_history_canonical(db_session, p.patient_id, "Hypertension for 5 years")
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        assert "Hypertension for 5 years" in data["history"]


class TestAC3NoDiagnosticLanguage:
    """
    AC-3 is the critical safety gate.
    All tests in this class must pass with zero exceptions.
    """

    def test_diagnoses_key_absent_from_panel_response(self, admin_client, db_session):
        """AC-3: 'diagnoses' key MUST NOT appear anywhere in the response JSON."""
        p = _seed_patient(db_session)
        _seed_diagnosis(db_session, p.patient_id, "Type 2 Diabetes", "E11")
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        assert "diagnoses" not in data, (
            "AC-3 VIOLATION: 'diagnoses' key found in context-panel response"
        )

    def test_icd10_code_absent_when_diagnosis_seeded(self, admin_client, db_session):
        """AC-3: icd10_code MUST NOT appear in any value within the panel response."""
        p = _seed_patient(db_session)
        _seed_diagnosis(db_session, p.patient_id, "Pneumonia", "J00")
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        response_text = str(data)
        assert "J00" not in response_text, (
            "AC-3 VIOLATION: ICD-10 code 'J00' found in context-panel response text"
        )
        assert "icd10_code" not in response_text, (
            "AC-3 VIOLATION: 'icd10_code' key found in context-panel response text"
        )

    def test_diagnosis_raw_text_not_surfaced_in_panel(self, admin_client, db_session):
        """
        AC-3: The raw_text of a Diagnosis row MUST NOT appear in any panel section.
        A Diagnosis row with raw_text='Pneumonia' must be invisible to the panel.
        """
        p = _seed_patient(db_session)
        _seed_diagnosis(db_session, p.patient_id, "Pneumonia", "J18.9")
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()

        all_texts = []
        for m in data.get("medications", []):
            all_texts.append(m.get("raw_text", ""))
        for r in data.get("prior_results", []):
            all_texts.append(r.get("raw_text", ""))
        all_texts.extend(data.get("allergies", []))
        all_texts.extend(data.get("history", []))

        assert "Pneumonia" not in all_texts, (
            "AC-3 VIOLATION: Diagnosis raw_text 'Pneumonia' surfaced in context panel"
        )

    def test_condition_name_key_absent_from_response(self, admin_client, db_session):
        """AC-3: 'condition_name' key must not appear anywhere in the response."""
        p = _seed_patient(db_session)
        _seed_diagnosis(db_session, p.patient_id, "Asthma", "J45")
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        assert "condition_name" not in str(data), (
            "AC-3 VIOLATION: 'condition_name' key found in context-panel response"
        )

    def test_panel_still_returns_medications_when_diagnosis_also_seeded(
        self, admin_client, db_session
    ):
        """
        AC-3 does not suppress other data.
        Medications must still appear even when a Diagnosis row exists.
        """
        p = _seed_patient(db_session)
        _seed_diagnosis(db_session, p.patient_id, "Hypertension", "I10")
        _seed_medication(db_session, p.patient_id, "Amlodipine 5mg", "329528")
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        raw_texts = [m["raw_text"] for m in data["medications"]]
        assert "Amlodipine 5mg" in raw_texts
        assert "diagnoses" not in data

    def test_allergy_present_and_no_diagnosis_when_both_seeded(self, admin_client, db_session):
        """AC-3: allergy section populated correctly even when Diagnosis row exists."""
        p = _seed_patient(db_session)
        _seed_allergy_canonical(db_session, p.patient_id, "Aspirin")
        _seed_diagnosis(db_session, p.patient_id, "Atrial Fibrillation", "I48")
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        assert "Aspirin" in data["allergies"]
        assert "diagnoses" not in data
        assert "I48" not in str(data)


class TestRBAC:

    def test_unauthenticated_request_returns_401(self, db_session):
        """No token → 401."""
        p = _seed_patient(db_session)
        c = TestClient(app)
        resp = c.get(f"/api/v1/patients/{p.patient_id}/context-panel")
        assert resp.status_code == 401

    def test_department_head_denied_403(self, db_session):
        """department_head role → 403 (not in RBAC_MATRIX for /patients)."""
        p = _seed_patient(db_session)
        c = _client_for("department_head")
        resp = c.get(f"/api/v1/patients/{p.patient_id}/context-panel")
        assert resp.status_code == 403

    def test_doctor_without_patient_access_denied_403(self, db_session):
        """doctor role without patient in patient_access → 403 from RbacAccessGuard."""
        p = _seed_patient(db_session)
        c = _client_for("doctor", patient_access=[])   # empty access list
        resp = c.get(f"/api/v1/patients/{p.patient_id}/context-panel")
        assert resp.status_code == 403

    def test_doctor_with_patient_access_gets_200(self, db_session):
        """doctor with patient_id in patient_access → 200."""
        p = _seed_patient(db_session)
        c = _client_for("doctor", patient_access=[p.patient_id])
        resp = c.get(f"/api/v1/patients/{p.patient_id}/context-panel")
        assert resp.status_code == 200

    def test_nurse_with_patient_access_gets_200(self, db_session):
        """nurse with patient_id in patient_access → 200."""
        p = _seed_patient(db_session)
        c = _client_for("nurse", patient_access=[p.patient_id])
        resp = c.get(f"/api/v1/patients/{p.patient_id}/context-panel")
        assert resp.status_code == 200

    def test_compliance_officer_denied_403(self, db_session):
        """compliance role → 403 (not in RBAC_MATRIX for /patients)."""
        p = _seed_patient(db_session)
        c = _client_for("compliance")
        resp = c.get(f"/api/v1/patients/{p.patient_id}/context-panel")
        assert resp.status_code == 403


class TestEdgeCases:

    def test_unknown_patient_id_returns_404(self, admin_client):
        """Non-existent patient → 404."""
        resp = admin_client.get(f"/api/v1/patients/{uuid.uuid4()}/context-panel")
        assert resp.status_code == 404

    def test_medications_list_type_is_list(self, admin_client, db_session):
        """medications section is always a list, never null."""
        p = _seed_patient(db_session)
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        assert isinstance(data["medications"], list)

    def test_allergies_list_type_is_list(self, admin_client, db_session):
        """allergies section is always a list, never null."""
        p = _seed_patient(db_session)
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        assert isinstance(data["allergies"], list)

    def test_prior_results_list_type_is_list(self, admin_client, db_session):
        """prior_results section is always a list, never null."""
        p = _seed_patient(db_session)
        data = admin_client.get(f"/api/v1/patients/{p.patient_id}/context-panel").json()
        assert isinstance(data["prior_results"], list)
