import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_patient_crud(client):
    # Create
    import uuid
    unique_mrn = f"MRN-{uuid.uuid4()}"
    resp = client.post("/api/v1/patients", json={
        "mrn": unique_mrn,
        "name": "John Doe",
        "dob": "1990-01-01",
        "sex": "Male"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["mrn"] == unique_mrn
    patient_id = data["patient_id"]
    
    # Get
    resp = client.get(f"/api/v1/patients/{patient_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "John Doe"
    
    # Update
    resp = client.patch(f"/api/v1/patients/{patient_id}", json={
        "name": "John Doe Updated"
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "John Doe Updated"
    
    # List
    resp = client.get("/api/v1/patients")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
