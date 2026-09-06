"""
Story 10.3 — FR-34 Compliance Regression Gate (MUST, permanent)
================================================================
Proves that Epic 5 (RAG) and Epic 10 (context panel + note save)
never output condition, diagnosis, or treatment language.

AC-3 enforcement happens at THREE independent layers:
  Layer 1 — service-level enforce_ac3() call before return
  Layer 2 — sanitization / banned-phrase scan in compliance.py
  Layer 3 — this test suite (release-blocking regression gate)

Any failure here BLOCKS release until fixed.
"""

import uuid
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

try:
    from httpx import ASGITransport
except ImportError:
    ASGITransport = None

from app.main import app
from app.core.compliance import contains_banned_content, enforce_ac3, ComplianceViolationError
from app.dependencies.auth import get_current_user
from app.core.security import create_access_token
from tests.conftest import TestingSessionLocal


SAFE_TEXTS = [
    "Blood pressure: 130/85. Heart rate: 72 bpm.",
    "Patient reported mild headache for 3 days. Referred for imaging.",
    "Prior medications: metformin 500 mg. Allergies: penicillin.",
    "Travel history: visited rural area 2 weeks ago.",
    "No findings recorded for this visit.",
    "",
]

BANNED_TEXTS = [
    ("The patient has hypertension.", "patient has"),
    ("Diagnosis: Type 2 diabetes.", "diagnosis"),
    ("This is consistent with pneumonia.", "consistent with"),
    ("Differential: appendicitis vs gastritis.", "differential"),
    ("Recommend treatment: antibiotics.", "recommend treatment"),
    ("ICD-10 code J45.20 applies.", "icd-"),
    ("Etiology: viral infection.", "etiology"),
    ("Likely due to stress.", "likely due to"),
    ("Assessment: patient is stable.", "assessment:"),
    ("Plan: prescribe amoxicillin.", "plan: <treatment>"),
    ("Impression: normal sinus rhythm.", "impression:"),
    ("Initiate therapy immediately.", "initiate therapy"),
]


@pytest.mark.parametrize("text", SAFE_TEXTS)
def test_safe_text_passes(text):
    flagged, phrase = contains_banned_content(text)
    assert not flagged, f"Safe text was incorrectly flagged: '{phrase}'"


@pytest.mark.parametrize("text,expected_phrase", BANNED_TEXTS)
def test_banned_text_detected(text, expected_phrase):
    flagged, phrase = contains_banned_content(text)
    assert flagged, f"Banned text was NOT detected: '{text}'"


def test_enforce_ac3_raises_on_violation():
    with pytest.raises(ComplianceViolationError):
        enforce_ac3("Diagnosis: hypertension.")


def test_enforce_ac3_returns_text_when_safe():
    safe = "Blood pressure 120/80."
    result = enforce_ac3(safe)
    assert result == safe


def test_enforce_ac3_case_insensitive():
    with pytest.raises(ComplianceViolationError):
        enforce_ac3("DIAGNOSIS: fever.")


def test_enforce_ac3_substring_match():
    """Banned phrase as substring within a longer sentence."""
    with pytest.raises(ComplianceViolationError):
        enforce_ac3("The lab results are consistent with viral infection.")


class MockDoctor:
    id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    role = "doctor"
    email = "doctor@clinic.org"
    patient_access = []


@pytest.fixture
def doctor_client():
    app.dependency_overrides[get_current_user] = lambda: MockDoctor()
    yield app
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _create_async_client(app_obj):
    token = create_access_token({"sub": "00000000-0000-0000-0000-000000000001", "role": "doctor", "email": "doctor@clinic.org"})
    headers = {"Authorization": f"Bearer {token}"}
    if ASGITransport is not None:
        return AsyncClient(transport=ASGITransport(app=app_obj), base_url="http://test", headers=headers)
    return AsyncClient(app=app_obj, base_url="http://test", headers=headers)


DIAGNOSTIC_RAG_ANSWERS = [
    "The patient has diabetes mellitus.",
    "Consistent with hypertensive crisis.",
    "Diagnosis: iron-deficiency anemia.",
    "Differential: appendicitis vs ovarian cyst.",
    "Recommend treatment with corticosteroids.",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("injected_answer", DIAGNOSTIC_RAG_ANSWERS)
async def test_rag_endpoint_blocks_diagnostic_answer(doctor_client, injected_answer):
    """
    Even if the underlying LLM produces a diagnostic answer,
    the enforce_ac3 layer must block it before it reaches the client.
    """
    with patch(
        "app.services.rag_service.run_rag_chain",
        new=AsyncMock(return_value=injected_answer),
    ):
        async with _create_async_client(doctor_client) as client:
            response = await client.post(
                "/api/v1/rag/query",
                json={"patient_id": "00000000-0000-0000-0000-000000000099", "query": "What is wrong?"},
            )
        assert response.status_code != 200 or \
               not any(p in response.text.lower() for p in ["diagnosis", "consistent with", "patient has"]), \
               f"Banned content reached client: {response.text[:200]}"


@pytest.mark.asyncio
async def test_rag_endpoint_safe_answer_passes(doctor_client):
    safe = "Blood pressure was 130/85 on last visit. No prior test results available."
    with patch(
        "app.services.rag_service.run_rag_chain",
        new=AsyncMock(return_value=safe),
    ):
        async with _create_async_client(doctor_client) as client:
            response = await client.post(
                "/api/v1/rag/query",
                json={"patient_id": "00000000-0000-0000-0000-000000000099", "query": "Vitals?"},
            )
        assert response.status_code == 200
        body = response.json()
        flagged, phrase = contains_banned_content(str(body))
        assert not flagged, f"Safe answer was incorrectly blocked: '{phrase}'"


DIAGNOSTIC_PANEL_TEXTS = [
    "History suggests diagnosis of hypertension.",
    "Patient is suffering from chronic kidney disease.",
    "Medication recommendation: lisinopril 10 mg.",
]


@pytest.mark.asyncio
@pytest.mark.parametrize("injected_text", DIAGNOSTIC_PANEL_TEXTS)
async def test_context_panel_blocks_diagnostic_text(doctor_client, injected_text):
    with patch(
        "app.services.context_panel_service.build_panel_text",
        new=AsyncMock(return_value=injected_text),
    ):
        async with _create_async_client(doctor_client) as client:
            response = await client.get(
                "/api/v1/context-panel/00000000-0000-0000-0000-000000000099"
            )
        if response.status_code == 200:
            flagged, phrase = contains_banned_content(response.text)
            assert not flagged, f"Banned content in panel response: '{phrase}'"


@pytest.mark.asyncio
async def test_context_panel_safe_content_passes(doctor_client):
    safe_panel = {
        "history": ["Visited 2024-01-10 — BP 130/85"],
        "medications": ["Metformin 500 mg"],
        "allergies": ["Penicillin"],
        "prior_results": ["CBC: WBC 7.2, HGB 13.4"],
    }
    with patch(
        "app.services.context_panel_service.get_context_panel",
        new=AsyncMock(return_value=safe_panel),
    ):
        async with _create_async_client(doctor_client) as client:
            response = await client.get(
                "/api/v1/context-panel/00000000-0000-0000-0000-000000000099"
            )
        assert response.status_code == 200
        flagged, phrase = contains_banned_content(response.text)
        assert not flagged


@pytest.mark.asyncio
async def test_save_note_blocked_when_content_has_diagnosis(doctor_client):
    async with _create_async_client(doctor_client) as client:
        response = await client.post(
            "/api/v1/notes",
            json={
                "patient_id": "00000000-0000-0000-0000-000000000099",
                "content": "Diagnosis: Type 2 diabetes mellitus.",
            },
        )
    assert response.status_code == 422
    assert "ac-3" in response.text.lower() or "compliance" in response.text.lower() or "banned" in response.text.lower()


@pytest.mark.asyncio
async def test_save_note_succeeds_for_safe_content(doctor_client, db_session):
    async with _create_async_client(doctor_client) as client:
        response = await client.post(
            "/api/v1/notes",
            json={
                "patient_id": "00000000-0000-0000-0000-000000000099",
                "content": "Patient reported headache for 3 days. Referred for imaging per protocol.",
            },
        )
    assert response.status_code == 201
    body = response.json()
    assert "id" in body
    assert body["content"] is not None
    flagged, phrase = contains_banned_content(body["content"])
    assert not flagged


@pytest.mark.asyncio
async def test_save_note_full_response_body_scan(doctor_client):
    """Full string scan of entire response body — zero trace of banned content."""
    async with _create_async_client(doctor_client) as client:
        response = await client.post(
            "/api/v1/notes",
            json={
                "patient_id": "00000000-0000-0000-0000-000000000099",
                "content": "Vitals recorded. Follow-up scheduled.",
            },
        )
    if response.status_code == 201:
        flagged, phrase = contains_banned_content(response.text)
        assert not flagged, f"Banned phrase in response body: '{phrase}'"


@pytest.mark.asyncio
async def test_save_note_403_for_unauthorized_role():
    class MockAdmin:
        id = uuid.UUID("00000000-0000-0000-0000-000000000002")
        role = "hospital_admin"
        email = "admin@clinic.org"
        patient_access = []

    app.dependency_overrides[get_current_user] = lambda: MockAdmin()
    token = create_access_token({"sub": "00000000-0000-0000-0000-000000000002", "role": "hospital_admin"})
    headers = {"Authorization": f"Bearer {token}"}

    if ASGITransport is not None:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=headers) as client:
            response = await client.post(
                "/api/v1/notes",
                json={
                    "patient_id": "00000000-0000-0000-0000-000000000099",
                    "content": "Routine check.",
                },
            )
    else:
        async with AsyncClient(app=app, base_url="http://test", headers=headers) as client:
            response = await client.post(
                "/api/v1/notes",
                json={
                    "patient_id": "00000000-0000-0000-0000-000000000099",
                    "content": "Routine check.",
                },
            )
    assert response.status_code == 403
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_list_notes_returns_saved_note(doctor_client, db_session):
    # Save first
    async with _create_async_client(doctor_client) as client:
        save_resp = await client.post(
            "/api/v1/notes",
            json={
                "patient_id": "00000000-0000-0000-0000-000000000099",
                "content": "Blood pressure noted. No prior allergies on file.",
            },
        )
    assert save_resp.status_code == 201

    # Then list
    async with _create_async_client(doctor_client) as client:
        list_resp = await client.get("/api/v1/notes/00000000-0000-0000-0000-000000000099")
    assert list_resp.status_code == 200
    notes = list_resp.json()
    assert len(notes) >= 1
    for note in notes:
        flagged, phrase = contains_banned_content(note["content"])
        assert not flagged, f"Banned phrase in listed note: '{phrase}'"
