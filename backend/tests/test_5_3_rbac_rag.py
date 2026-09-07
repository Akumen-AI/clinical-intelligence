"""
Story 5.3 (FR-20) — RBAC-scoped RAG access tests.

Acceptance criteria:
  AC-1  Query pipeline checks requesting user's role before retrieval.
  AC-2  Unauthorized patient queries return access-denied, not a partial answer.
  AC-3  At least one automated test per role covers this check.
"""
import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from app.main import app
from app.models.patient import Patient
from app.models.rag_chunk import PatientRAGChunk
from app.core.security import get_current_user, User
from tests.conftest import TestingSessionLocal

client = TestClient(app)

# ── helpers ──────────────────────────────────────────────────────────────────

from app.models.user import User, UserRole

def _user(role: str) -> User:
    try:
        enum_role = UserRole(role)
    except ValueError:
        enum_role = UserRole.NURSE
    u = User(id=uuid.uuid4(), role=enum_role, email=f"{role}@clinic.org")
    u.patient_access = [f"patient_rbac_{role}", f"patient_denied_{role}", "patient_no_leak"]
    return u

def _override(role: str):
    user = _user(role)
    app.dependency_overrides[get_current_user] = lambda: user

def _clear():
    app.dependency_overrides.pop(get_current_user, None)

def _seed_patient_with_chunk(patient_id: str, mrn: str):
    """Seed a patient + one RAG chunk into the test DB."""
    db = TestingSessionLocal()
    try:
        db.add(Patient(patient_id=patient_id, mrn=mrn, name="RBAC Test Patient"))
        db.add(PatientRAGChunk(
            patient_id=patient_id,
            source_document_id="doc-rbac-1",
            content="Patient was prescribed Metformin 500mg.",
            embedding=[0.1, 0.2, 0.3],
            metadata_json={"document_type": "Prescription"},
        ))
        db.commit()
    finally:
        db.close()

# ── AC-1 + AC-3: allowed roles reach the RAG pipeline ────────────────────────

@pytest.mark.parametrize("role", ["doctor", "nurse", "hospital_admin"])
@patch("app.config.settings.GEMINI_API_KEY", "dummy_key")
@patch("google.genai.Client")
def test_allowed_role_reaches_rag(mock_genai, role):
    """AC-1 / AC-3: roles in CLINICAL_READ_ROLES get a 200 response from /ask."""
    patient_id = f"patient_rbac_{role}"
    _seed_patient_with_chunk(patient_id, f"MRN-{role.upper()}")
    _override(role)

    mock_instance = mock_genai.return_value
    mock_instance.models.embed_content.return_value = MagicMock(
        embeddings=[MagicMock(values=[0.1, 0.2, 0.3])]
    )
    mock_instance.models.generate_content.return_value = MagicMock(
        text="Metformin 500mg recorded on file."
    )


    try:
        resp = client.post(
            f"/api/v1/patients/{patient_id}/ask",
            json={"question": "What medication was prescribed?"},
        )
        assert resp.status_code == 200, f"Expected 200 for role={role}, got {resp.status_code}"
        data = resp.json()
        assert "answer" in data
        assert data["answer"] != ""
    finally:
        _clear()

# ── AC-2 + AC-3: denied roles get 403, not a partial answer ──────────────────

@pytest.mark.parametrize("role", ["it", "compliance", "department_head"])
@patch("app.config.settings.GEMINI_API_KEY", "dummy_key")
def test_denied_role_gets_403_not_partial_answer(role):
    """AC-2 / AC-3: roles outside CLINICAL_READ_ROLES receive 403, zero data."""
    patient_id = f"patient_denied_{role}"
    _seed_patient_with_chunk(patient_id, f"MRN-DENIED-{role.upper()}")
    _override(role)

    try:
        resp = client.post(
            f"/api/v1/patients/{patient_id}/ask",
            json={"question": "What medication was prescribed?"},
        )
        assert resp.status_code == 403, f"Expected 403 for role={role}, got {resp.status_code}"
        data = resp.json()
        assert "Access denied: role" in data["detail"]
        # Confirm no answer field leaked
        assert "answer" not in data
        assert "source_documents" not in data
    finally:
        _clear()

# ── AC-3: unauthenticated → 401 ──────────────────────────────────────────────

def test_unauthenticated_ask_returns_401():
    """AC-3: no bearer token → 401 before any retrieval."""
    old_override = app.dependency_overrides.pop(get_current_user, None)
    try:
        resp = client.post(
            "/api/v1/patients/any_patient/ask",
            json={"question": "Hello?"},
        )
        assert resp.status_code == 401
    finally:
        if old_override:
            app.dependency_overrides[get_current_user] = old_override

# ── RBAC also gates list + get patient endpoints ─────────────────────────────

@patch("app.config.settings.GEMINI_API_KEY", "dummy_key")
def test_denied_role_cannot_list_patients():
    """IT role must not read the patient list."""
    _override("it")
    try:
        resp = client.get("/api/v1/patients")
        assert resp.status_code == 403
        assert "Access denied: role" in resp.json()["detail"]
    finally:
        _clear()

@patch("app.config.settings.GEMINI_API_KEY", "dummy_key")
def test_denied_role_cannot_get_patient_records():
    """Compliance role must not read patient clinical records."""
    _override("compliance")
    try:
        resp = client.get("/api/v1/patients/some_id/records")
        assert resp.status_code == 403
        assert "Access denied: role" in resp.json()["detail"]
    finally:
        _clear()

@pytest.mark.parametrize("role", ["doctor", "nurse"])
@patch("app.config.settings.GEMINI_API_KEY", "dummy_key")
def test_allowed_role_can_list_patients(role):
    """Doctor and nurse can list patients."""
    _override(role)
    try:
        resp = client.get("/api/v1/patients")
        assert resp.status_code == 200
    finally:
        _clear()

# ── 403 body must not contain any patient data ───────────────────────────────

@patch("app.config.settings.GEMINI_API_KEY", "dummy_key")
def test_403_response_body_contains_no_patient_data():
    """
    Even if the patient exists and has chunks, a denied role gets a 403 whose
    body contains no clinical data — only the access-denied detail string.
    """
    patient_id = "patient_no_leak"
    _seed_patient_with_chunk(patient_id, "MRN-NOLEAK")
    _override("it")

    try:
        resp = client.post(
            f"/api/v1/patients/{patient_id}/ask",
            json={"question": "What is the patient's diagnosis?"},
        )
        assert resp.status_code == 403
        body_text = resp.text
        # Clinical terms from the seeded chunk must not appear in the 403 body
        assert "Metformin" not in body_text
        assert "Prescription" not in body_text
        assert patient_id not in body_text or "Access denied" in body_text
    finally:
        _clear()
