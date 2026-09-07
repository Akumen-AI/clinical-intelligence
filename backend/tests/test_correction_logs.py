import hashlib
import uuid
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from app.main import app
from app.db.base import Base
from app.db.session import get_async_db
from app.core.security import create_access_token
from app.models.document import Document
from app.models.extracted_field import ExtractedField
from app.models.pending_review import PendingReview, ReviewStatus
from app.models.correction_log import CorrectionLog
from app.models.user import User, UserRole
from app.schemas.correction_log import CorrectionAction



@pytest.fixture
def reviewer_id():
    return uuid.uuid4()

@pytest.fixture
def auth_headers(reviewer_id):
    token = create_access_token(data={"sub": str(reviewer_id), "role": "hospital_admin"})
    return {"Authorization": f"Bearer {token}"}

@pytest_asyncio.fixture
async def seed_extracted_field(db_session, reviewer_id):
    doc_id = uuid.uuid4()
    field_id = uuid.uuid4()

    # Seed User if needed
    user = User(id=reviewer_id, email="nurse@clinic.org", role=UserRole.NURSE)
    db_session.add(user)

    doc = Document(
        document_id=str(doc_id),
        filename="test_patient_chart.pdf",
        raw_uri="uploads/test_patient_chart.pdf",
        filetype="pdf",
        status="extracted",
    )
    db_session.add(doc)

    field = ExtractedField(
        field_id=str(field_id),
        document_id=str(doc_id),
        field_name="patient_name",
        raw_value="John Doe",
        confidence_score=0.65,
        verification_status="extracted",
    )
    db_session.add(field)

    pending = PendingReview(
        id=str(uuid.uuid4()),
        document_id=str(doc_id),
        field_name="patient_name",
        extracted_value="John Doe",
        confidence_score=0.65,
        status=ReviewStatus.PENDING,
    )
    db_session.add(pending)

    await db_session.commit()

    return {
        "document_id": doc_id,
        "extracted_field_id": field_id,
        "field_name": "patient_name",
        "before_value": "John Doe",
        "confidence_score": 0.65,
        "reviewer_id": reviewer_id,
    }


# --- Test Cases ---

@pytest.mark.asyncio
async def test_log_accept_persists_verified_at(async_client, auth_headers, seed_extracted_field):
    """accept action sets verified_at to a non-null datetime"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "accept",
        "before_value": seed_extracted_field["before_value"],
        "field_name": seed_extracted_field["field_name"],
        "confidence_score": seed_extracted_field["confidence_score"],
    }
    response = await async_client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["action"] == "accept"
    assert data["verified_at"] is not None
    assert data["after_value"] == seed_extracted_field["before_value"]


@pytest.mark.asyncio
async def test_log_edit_sets_after_value(async_client, auth_headers, seed_extracted_field):
    """edit action stores the corrected after_value"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "edit",
        "before_value": seed_extracted_field["before_value"],
        "after_value": "Jane Doe",
        "field_name": seed_extracted_field["field_name"],
        "confidence_score": seed_extracted_field["confidence_score"],
    }
    response = await async_client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["action"] == "edit"
    assert data["after_value"] == "Jane Doe"
    assert data["verified_at"] is not None


@pytest.mark.asyncio
async def test_log_reject_leaves_verified_at_null(async_client, auth_headers, seed_extracted_field):
    """reject action must leave verified_at as NULL"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "reject",
        "before_value": seed_extracted_field["before_value"],
        "field_name": seed_extracted_field["field_name"],
        "confidence_score": seed_extracted_field["confidence_score"],
    }
    response = await async_client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["action"] == "reject"
    assert data["verified_at"] is None
    assert data["after_value"] is None


@pytest.mark.asyncio
async def test_accept_removes_from_pending_queue(async_client, auth_headers, db_session, seed_extracted_field):
    """after accept, the field must no longer appear in pending_review_queue"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "accept",
        "before_value": seed_extracted_field["before_value"],
        "field_name": seed_extracted_field["field_name"],
    }
    res = await async_client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)
    assert res.status_code == 201

    stmt = select(PendingReview).where(PendingReview.document_id == str(seed_extracted_field["document_id"]))
    result = await db_session.execute(stmt)
    assert len(result.scalars().all()) == 0


@pytest.mark.asyncio
async def test_reject_leaves_field_in_pending_queue(async_client, auth_headers, db_session, seed_extracted_field):
    """after reject, the field stays in pending_review_queue"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "reject",
        "before_value": seed_extracted_field["before_value"],
        "field_name": seed_extracted_field["field_name"],
    }
    res = await async_client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)
    assert res.status_code == 201

    stmt = select(PendingReview).where(PendingReview.document_id == str(seed_extracted_field["document_id"]))
    result = await db_session.execute(stmt)
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_get_logs_for_document(async_client, auth_headers, seed_extracted_field):
    """GET /document/{id} returns all logs ordered by reviewed_at"""
    doc_id = str(seed_extracted_field["document_id"])
    field_id = str(seed_extracted_field["extracted_field_id"])

    payload1 = {
        "extracted_field_id": field_id,
        "document_id": doc_id,
        "action": "edit",
        "before_value": "Val1",
        "after_value": "Val2",
        "field_name": "dosage",
    }
    payload2 = {
        "extracted_field_id": field_id,
        "document_id": doc_id,
        "action": "accept",
        "before_value": "Val2",
        "field_name": "dosage",
    }
    await async_client.post("/api/v1/correction-logs/", json=payload1, headers=auth_headers)
    await async_client.post("/api/v1/correction-logs/", json=payload2, headers=auth_headers)

    res = await async_client.get(f"/api/v1/correction-logs/document/{doc_id}", headers=auth_headers)
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) == 2
    assert logs[0]["action"] == "edit"
    assert logs[1]["action"] == "accept"


@pytest.mark.asyncio
async def test_export_phi_field_returns_hash_not_plaintext(async_client, auth_headers, seed_extracted_field):
    """export row for patient_name must contain a SHA-256 hash, never the raw name"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "edit",
        "before_value": "John Doe",
        "after_value": "Johnny Doe",
        "field_name": "patient_name",
    }
    await async_client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)

    export_res = await async_client.post("/api/v1/correction-logs/export/retraining", headers=auth_headers)
    assert export_res.status_code == 200
    batch = export_res.json()
    assert batch["exported_count"] == 1
    row = batch["rows"][0]
    expected_before_hash = hashlib.sha256("John Doe".encode()).hexdigest()
    expected_after_hash = hashlib.sha256("Johnny Doe".encode()).hexdigest()
    assert row["before_value_hash"] == expected_before_hash
    assert row["after_value_hash"] == expected_after_hash
    assert "John Doe" not in str(row)
    assert "Johnny Doe" not in str(row)


@pytest.mark.asyncio
async def test_export_non_phi_field_returns_raw_value(async_client, auth_headers, seed_extracted_field):
    """export row for diagnosis_code returns the value as-is"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "accept",
        "before_value": "E11.9",
        "field_name": "diagnosis_code",
    }
    await async_client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)

    export_res = await async_client.post("/api/v1/correction-logs/export/retraining", headers=auth_headers)
    assert export_res.status_code == 200
    batch = export_res.json()
    assert batch["exported_count"] == 1
    row = batch["rows"][0]
    assert row["before_value_hash"] == "E11.9"
    assert row["after_value_hash"] == "E11.9"


@pytest.mark.asyncio
async def test_export_marks_logs_as_exported(async_client, auth_headers, db_session, seed_extracted_field):
    """after export, retraining_exported=True and export_batch_id is set"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "accept",
        "before_value": "TestVal",
        "field_name": "test_field",
    }
    create_res = await async_client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)
    log_id = uuid.UUID(create_res.json()["id"])

    export_res = await async_client.post("/api/v1/correction-logs/export/retraining", headers=auth_headers)
    assert export_res.status_code == 200
    batch_id = export_res.json()["batch_id"]

    stmt = select(CorrectionLog).where(CorrectionLog.id == log_id)
    result = await db_session.execute(stmt)
    log = result.scalar_one()
    assert log.retraining_exported is True
    assert log.export_batch_id == batch_id


@pytest.mark.asyncio
async def test_double_export_does_not_duplicate(async_client, auth_headers, seed_extracted_field):
    """calling export twice should yield 0 rows on the second call"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "accept",
        "before_value": "TestVal",
        "field_name": "test_field",
    }
    await async_client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)

    res1 = await async_client.post("/api/v1/correction-logs/export/retraining", headers=auth_headers)
    assert res1.status_code == 200
    assert res1.json()["exported_count"] == 1

    res2 = await async_client.post("/api/v1/correction-logs/export/retraining", headers=auth_headers)
    assert res2.status_code == 200
    assert res2.json()["exported_count"] == 0
    assert len(res2.json()["rows"]) == 0


@pytest.mark.asyncio
async def test_log_not_found_returns_404(async_client, auth_headers):
    """GET /correction-logs/{random_uuid} → 404"""
    random_id = str(uuid.uuid4())
    res = await async_client.get(f"/api/v1/correction-logs/{random_id}", headers=auth_headers)
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401(async_client, seed_extracted_field):
    """POST without auth header → 401"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "accept",
        "before_value": "TestVal",
        "field_name": "test_field",
    }
    res = await async_client.post("/api/v1/correction-logs/", json=payload)
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_api_export_writes_audit_log(async_client, auth_headers, db_session, seed_extracted_field, reviewer_id):
    """Triggering export via API logs the export with the human actor's ID."""
    from app.models.audit_log import AuditLogEntry
    # clear audit log
    await db_session.execute(select(AuditLogEntry).filter(AuditLogEntry.action_type == "correction_log_export"))
    
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "accept",
        "before_value": "TestVal",
        "field_name": "test_field",
    }
    await async_client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)

    export_res = await async_client.post("/api/v1/correction-logs/export/retraining", headers=auth_headers)
    assert export_res.status_code == 200
    batch_id = export_res.json()["batch_id"]

    result = await db_session.execute(
        select(AuditLogEntry).filter(AuditLogEntry.action_type == "correction_log_export")
    )
    logs = result.scalars().all()
    assert len(logs) == 1
    
    audit_log = logs[0]
    assert audit_log.actor_user_id == reviewer_id
    assert audit_log.target_entity == f"export_batch:{batch_id}"
    assert audit_log.patient_id is None
    assert f"Exported 1 corrections in batch {batch_id}" in audit_log.rationale


@pytest.mark.asyncio
async def test_scheduled_export_writes_audit_log_with_system_actor(async_client, auth_headers, db_session, seed_extracted_field):
    """Calling export_for_retraining with actor_user_id=None logs it as the SYSTEM_ACTOR_ID."""
    from app.models.audit_log import AuditLogEntry
    from app.services.correction_log_service import CorrectionLogService
    from app.services.audit_service import SYSTEM_ACTOR_ID

    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "edit",
        "before_value": "TestVal",
        "after_value": "TestVal2",
        "field_name": "test_field2",
    }
    await async_client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)

    service = CorrectionLogService()
    batch_res = await service.export_for_retraining(db_session)
    batch_id = batch_res.batch_id

    result = await db_session.execute(
        select(AuditLogEntry).filter(AuditLogEntry.action_type == "correction_log_export").order_by(AuditLogEntry.timestamp.desc())
    )
    logs = result.scalars().all()
    assert len(logs) >= 1
    
    audit_log = logs[0]
    assert audit_log.actor_user_id == SYSTEM_ACTOR_ID
    assert audit_log.target_entity == f"export_batch:{batch_id}"
    assert f"Exported" in audit_log.rationale
