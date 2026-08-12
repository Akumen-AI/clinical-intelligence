import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_patient_crud():
    # Create
    resp = client.post("/api/v1/patients", json={
        "mrn": "MRN-12345",
        "name": "John Doe",
        "dob": "1990-01-01",
        "sex": "Male"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["mrn"] == "MRN-12345"
    patient_id = data["patient_id"]
    
    # Get
    resp = client.get(f"/api/v1/patients/{patient_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "John Doe"
    
    # Update
    resp = client.put(f"/api/v1/patients/{patient_id}", json={
        "name": "John Doe Updated"
    })
    assert resp.status_code == 200
    assert resp.json()["name"] == "John Doe Updated"
    
    # List
    resp = client.get("/api/v1/patients")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1
