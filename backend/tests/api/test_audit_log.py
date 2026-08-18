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
    response = client.get(f"/api/v1/audit-log/patient/{patient_id}", headers=headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)
