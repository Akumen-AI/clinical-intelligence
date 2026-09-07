import pytest
import uuid
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TestingSessionLocal
from app.models.patient import Patient
from app.models.clinical_entities import Medication, LabResult
from app.models.audit_log import AuditLogEntry
from app.core.security import create_access_token

client = TestClient(app)

def get_doctor_token(patient_id: str):
    return create_access_token(
        data={"sub": str(uuid.uuid4()), "role": "doctor", "email": "doctor@clinic.org", "patient_access": [patient_id]}
    )

def get_hospital_admin_token():
    return create_access_token(
        data={"sub": str(uuid.uuid4()), "role": "hospital_admin", "email": "admin@clinic.org"}
    )

def test_patient_dashboard_audit_logging():
    db = TestingSessionLocal()
    db.query(AuditLogEntry).delete()
    db.query(LabResult).filter(LabResult.patient_id == "test-dashboard-patient").delete()
    db.query(Medication).filter(Medication.patient_id == "test-dashboard-patient").delete()
    db.query(Patient).filter(Patient.patient_id == "test-dashboard-patient").delete()
    db.commit()

    patient_id = "test-dashboard-patient"
    patient = Patient(patient_id=patient_id, mrn="MRN-DB", name="Dashboard Test")
    db.add(patient)
    
    med = Medication(patient_id=patient_id, raw_text="Aspirin", source_field_id=str(uuid.uuid4()))
    db.add(med)
    
    lab = LabResult(patient_id=patient_id, test_name="Hemoglobin", value_numeric=14.0, raw_text="Hemoglobin 14", source_field_id=str(uuid.uuid4()))
    db.add(lab)
    
    db.commit()
    db.close()

    token = get_doctor_token(patient_id)
    headers = {"Authorization": f"Bearer {token}"}
    
    response = client.get(f"/api/v1/dashboards/patient/{patient_id}", headers=headers)
    assert response.status_code == 200

    db = TestingSessionLocal()
    logs = db.query(AuditLogEntry).filter(AuditLogEntry.action_type == "patient_dashboard_viewed").all()
    assert len(logs) == 1
    assert logs[0].patient_id == patient_id
    assert logs[0].target_entity == f"patient:{patient_id}"
    assert "1 medications" in logs[0].rationale
    assert "1 lab results" in logs[0].rationale
    db.close()

def test_operational_dashboards_audit_logging():
    db = TestingSessionLocal()
    db.query(AuditLogEntry).delete()
    db.commit()
    db.close()

    token = get_hospital_admin_token()
    headers = {"Authorization": f"Bearer {token}"}
    
    # Department dashboard
    dept_response = client.get("/api/v1/dashboards/department?department=cardiology", headers=headers)
    assert dept_response.status_code == 200
    
    # Hospital dashboard
    hosp_response = client.get("/api/v1/dashboards/hospital", headers=headers)
    assert hosp_response.status_code == 200

    db = TestingSessionLocal()
    dept_logs = db.query(AuditLogEntry).filter(AuditLogEntry.action_type == "department_dashboard_viewed").all()
    assert len(dept_logs) == 1
    assert dept_logs[0].patient_id is None
    assert dept_logs[0].target_entity == "department:cardiology"

    hosp_logs = db.query(AuditLogEntry).filter(AuditLogEntry.action_type == "hospital_dashboard_viewed").all()
    assert len(hosp_logs) == 1
    assert hosp_logs[0].patient_id is None
    assert hosp_logs[0].target_entity == "hospital"
    db.close()
