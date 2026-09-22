import hashlib
import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import select

from app.main import app
from app.db.base import Base
from app.core.security import create_access_token
from app.models.document import Document
from app.models.extracted_field import ExtractedField
from app.models.pending_review import PendingReview, ReviewStatus
from app.models.correction_log import CorrectionLog
from app.models.user import User, UserRole
from app.schemas.correction_log import CorrectionAction
from tests.conftest import TestingSessionLocal


@pytest.fixture
def reviewer_id():
    return uuid.uuid4()

@pytest.fixture
def auth_headers(reviewer_id):
    token = create_access_token(data={"sub": str(reviewer_id), "role": "hospital_admin"})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture
def seed_extracted_field(db_session, reviewer_id):
    doc_id = uuid.uuid4()
    field_id = uuid.uuid4()

    user = User(id=reviewer_id, email="admin@clinic.org", role=UserRole.HOSPITAL_ADMIN)
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

    db_session.commit()

    return {
        "document_id": doc_id,
        "extracted_field_id": field_id,
        "field_name": "patient_name",
        "before_value": "John Doe",
        "confidence_score": 0.65,
        "reviewer_id": reviewer_id,
    }


# --- Test Cases ---

def test_log_accept_persists_verified_at(client, auth_headers, seed_extracted_field):
    """accept action sets verified_at to a non-null datetime"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "accept",
        "before_value": seed_extracted_field["before_value"],
        "field_name": seed_extracted_field["field_name"],
        "confidence_score": seed_extracted_field["confidence_score"],
    }
    response = client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["action"] == "accept"
    assert data["verified_at"] is not None
    assert data["after_value"] == seed_extracted_field["before_value"]


def test_log_edit_sets_after_value(client, auth_headers, seed_extracted_field):
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
    response = client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["action"] == "edit"
    assert data["after_value"] == "Jane Doe"
    assert data["verified_at"] is not None


def test_log_reject_leaves_verified_at_null(client, auth_headers, seed_extracted_field):
    """reject action must leave verified_at as NULL"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "reject",
        "before_value": seed_extracted_field["before_value"],
        "field_name": seed_extracted_field["field_name"],
        "confidence_score": seed_extracted_field["confidence_score"],
    }
    response = client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["action"] == "reject"
    assert data["verified_at"] is None
    assert data["after_value"] is None


def test_accept_removes_from_pending_queue(client, auth_headers, db_session, seed_extracted_field):
    """after accept, the field must no longer appear in pending_review_queue"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "accept",
        "before_value": seed_extracted_field["before_value"],
        "field_name": seed_extracted_field["field_name"],
    }
    res = client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)
    assert res.status_code == 201

    queue_items = db_session.query(PendingReview).filter(PendingReview.document_id == str(seed_extracted_field["document_id"])).all()
    assert len(queue_items) == 0


def test_reject_leaves_field_in_pending_queue(client, auth_headers, db_session, seed_extracted_field):
    """after reject, the field stays in pending_review_queue"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "reject",
        "before_value": seed_extracted_field["before_value"],
        "field_name": seed_extracted_field["field_name"],
    }
    res = client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)
    assert res.status_code == 201

    queue_items = db_session.query(PendingReview).filter(PendingReview.document_id == str(seed_extracted_field["document_id"])).all()
    assert len(queue_items) == 1


def test_get_logs_for_document(client, auth_headers, seed_extracted_field):
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
    client.post("/api/v1/correction-logs/", json=payload1, headers=auth_headers)
    client.post("/api/v1/correction-logs/", json=payload2, headers=auth_headers)

    res = client.get(f"/api/v1/correction-logs/document/{doc_id}", headers=auth_headers)
    assert res.status_code == 200
    logs = res.json()
    assert len(logs) == 2
    assert logs[0]["action"] == "edit"
    assert logs[1]["action"] == "accept"


def test_export_phi_field_returns_hash_not_plaintext(client, auth_headers, seed_extracted_field):
    """export row for patient_name must contain a SHA-256 hash, never the raw name"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "edit",
        "before_value": "John Doe",
        "after_value": "Johnny Doe",
        "field_name": "patient_name",
    }
    client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)

    export_res = client.post("/api/v1/correction-logs/export/retraining", headers=auth_headers)
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


def test_export_non_phi_field_returns_raw_value(client, auth_headers, seed_extracted_field):
    """export row for diagnosis_code returns the value as-is"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "accept",
        "before_value": "E11.9",
        "field_name": "diagnosis_code",
    }
    client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)

    export_res = client.post("/api/v1/correction-logs/export/retraining", headers=auth_headers)
    assert export_res.status_code == 200
    batch = export_res.json()
    assert batch["exported_count"] == 1
    row = batch["rows"][0]
    assert row["before_value_hash"] == "E11.9"
    assert row["after_value_hash"] == "E11.9"


def test_export_marks_logs_as_exported(client, auth_headers, db_session, seed_extracted_field):
    """after export, retraining_exported=True and export_batch_id is set"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "accept",
        "before_value": "TestVal",
        "field_name": "test_field",
    }
    create_res = client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)
    log_id = create_res.json()["id"]

    export_res = client.post("/api/v1/correction-logs/export/retraining", headers=auth_headers)
    assert export_res.status_code == 200
    batch_id = export_res.json()["batch_id"]

    import uuid
    log = db_session.query(CorrectionLog).filter(CorrectionLog.id == uuid.UUID(log_id)).one()
    assert log.retraining_exported is True
    assert log.export_batch_id == batch_id


def test_double_export_does_not_duplicate(client, auth_headers, seed_extracted_field):
    """calling export twice should yield 0 rows on the second call"""
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "accept",
        "before_value": "TestVal",
        "field_name": "test_field",
    }
    client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)

    res1 = client.post("/api/v1/correction-logs/export/retraining", headers=auth_headers)
    assert res1.status_code == 200
    assert res1.json()["exported_count"] == 1

    res2 = client.post("/api/v1/correction-logs/export/retraining", headers=auth_headers)
    assert res2.status_code == 200
    assert res2.json()["exported_count"] == 0
    assert len(res2.json()["rows"]) == 0


def test_log_not_found_returns_404(client, auth_headers):
    """GET /correction-logs/{random_uuid} → 404"""
    random_id = str(uuid.uuid4())
    res = client.get(f"/api/v1/correction-logs/{random_id}", headers=auth_headers)
    assert res.status_code == 404


def test_unauthenticated_request_returns_401(client, seed_extracted_field):
    """POST without auth header → 401"""
    client.cookies.clear()
    client.headers.pop("Authorization", None)
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "accept",
        "before_value": "TestVal",
        "field_name": "test_field",
    }
    res = client.post("/api/v1/correction-logs/", json=payload)
    assert res.status_code == 401


def test_api_export_writes_audit_log(client, auth_headers, db_session, seed_extracted_field, reviewer_id):
    """Triggering export via API logs the export with the human actor's ID."""
    from app.models.audit_log import AuditLogEntry
    db_session.query(AuditLogEntry).filter(AuditLogEntry.action_type == "correction_log_export").delete()
    db_session.commit()
    
    payload = {
        "extracted_field_id": str(seed_extracted_field["extracted_field_id"]),
        "document_id": str(seed_extracted_field["document_id"]),
        "action": "accept",
        "before_value": "TestVal",
        "field_name": "test_field",
    }
    client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)

    export_res = client.post("/api/v1/correction-logs/export/retraining", headers=auth_headers)
    assert export_res.status_code == 200
    batch_id = export_res.json()["batch_id"]

    logs = db_session.query(AuditLogEntry).filter(AuditLogEntry.action_type == "correction_log_export").all()
    assert len(logs) == 1
    
    audit_log = logs[0]
    assert audit_log.actor_user_id == reviewer_id
    assert audit_log.target_entity == f"export_batch:{batch_id}"
    assert audit_log.patient_id is None
    assert f"Exported 1 corrections in batch {batch_id}" in audit_log.rationale


def test_scheduled_export_writes_audit_log_with_system_actor(client, auth_headers, db_session, seed_extracted_field):
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
    client.post("/api/v1/correction-logs/", json=payload, headers=auth_headers)

    service = CorrectionLogService()
    batch_res = service.export_for_retraining(db_session)
    batch_id = batch_res.batch_id

    logs = db_session.query(AuditLogEntry).filter(AuditLogEntry.action_type == "correction_log_export").order_by(AuditLogEntry.timestamp.desc()).all()
    assert len(logs) >= 1
    
    audit_log = logs[0]
    assert str(audit_log.actor_user_id) == str(SYSTEM_ACTOR_ID)
    assert audit_log.target_entity == f"export_batch:{batch_id}"
    assert f"Exported" in audit_log.rationale

def test_correction_logs_denied_for_doctor(client_as):
    client = client_as("doctor")
    assert client.post("/api/v1/correction-logs/").status_code == 403
    assert client.get("/api/v1/correction-logs/123").status_code == 403
    assert client.get("/api/v1/correction-logs/document/doc123").status_code == 403

