import pytest
from fastapi.testclient import TestClient
import uuid
from app.main import app
from app.core.security import create_access_token

client = TestClient(app)

def get_compliance_token():
    return create_access_token(data={"sub": str(uuid.uuid4()), "role": "compliance", "email": "compliance@clinic.org"})

def get_doctor_token():
    return create_access_token(data={"sub": str(uuid.uuid4()), "role": "doctor", "email": "doctor@clinic.org"})

def test_audit_log_append_only():
    token = get_compliance_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to PATCH
    patch_response = client.patch("/api/v1/audit-log", headers=headers)
    assert patch_response.status_code == 405 # Method Not Allowed
    
    # Try to DELETE
    delete_response = client.delete("/api/v1/audit-log", headers=headers)
    assert delete_response.status_code == 405

def test_get_audit_logs_compliance_role():
    # Test compliance access
    token = get_compliance_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/audit-log", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_get_audit_logs_doctor_role_forbidden():
    # Test doctor access (should be 403)
    token = get_doctor_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/audit-log", headers=headers)
    assert response.status_code == 403

def test_get_patient_audit_logs():
    token = get_compliance_token()
    headers = {"Authorization": f"Bearer {token}"}
    patient_id = "test-patient-123"
    other_patient_id = "test-patient-456"
    
    # Seed data
    from tests.conftest import TestingSessionLocal
    from app.services import audit_service
    import uuid
    from app.models.audit_log import AuditLogEntry
    db = TestingSessionLocal()
    actor_id = uuid.uuid4()
    
    audit_service.write_entry(db, actor_id, "document_uploaded", "document:doc123", patient_id=patient_id)
    audit_service.write_entry(db, actor_id, "canonical_record_write", "canonical_record:can123", patient_id=patient_id)
    audit_service.write_entry(db, actor_id, "review_approve", "pending_review:rev123", patient_id=patient_id)
    audit_service.write_entry(db, actor_id, "document_uploaded", "document:doc456", patient_id=other_patient_id)
    db.close()
    
    response = client.get(f"/api/v1/audit-log/patient/{patient_id}", headers=headers)
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)
    assert len(logs) == 3
    action_types = {log["action_type"] for log in logs}
    assert action_types == {"document_uploaded", "canonical_record_write", "review_approve"}
    assert all(log["patient_id"] == patient_id for log in logs)
    
    response_other = client.get(f"/api/v1/audit-log/patient/{other_patient_id}", headers=headers)
    logs_other = response_other.json()
    assert len(logs_other) == 1
    assert logs_other[0]["patient_id"] == other_patient_id
