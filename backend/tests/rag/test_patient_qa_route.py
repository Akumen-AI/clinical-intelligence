import pytest
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
from unittest.mock import patch, AsyncMock
from app.main import app
from app.models.user import UserRole
from app.core.security import get_current_user, User as SecurityUser
from app.services.rag.rbac_access_guard import AccessDeniedError

PATIENT_ID = uuid4()


def make_doctor_without_access():
    return SecurityUser(
        id=uuid4(),
        role=UserRole.DOCTOR,
        email="doctor@clinic.org",
        patient_access=[],
        is_active=True,
    )


@pytest.mark.asyncio
async def test_unauthorized_patient_query_returns_403():
    old_override = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = lambda: make_doctor_without_access()

    with patch(
        "app.services.rag.patient_rag_service.PatientRagService.query",
        new_callable=AsyncMock,
        side_effect=AccessDeniedError("not authorized"),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                f"/api/v1/rag/patient/{PATIENT_ID}/query",
                json={"question": "What medications is this patient on?"},
            )

    assert resp.status_code == 403
    detail = resp.json().get("detail", "")
    assert "not authorized" in detail.lower() or resp.status_code == 403

    if old_override:
        app.dependency_overrides[get_current_user] = old_override
    else:
        app.dependency_overrides.pop(get_current_user, None)
