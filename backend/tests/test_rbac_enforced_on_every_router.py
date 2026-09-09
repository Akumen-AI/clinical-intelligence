import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_rbac_enforced_on_every_router():
    """
    Ensure the 7 routers that had the 'Double Router-Registration Bug'
    are properly guarded by check_rbac.
    """
    unauthed_client = TestClient(app)

    routes_to_test = [
        ("GET", "/api/v1/documents"),
        ("POST", "/api/v1/documents/upload"),
        ("GET", "/api/v1/documents/123/layout"),
        ("POST", "/api/v1/documents/123/extract"),
        ("GET", "/api/v1/timeline"),
        ("GET", "/api/v1/canonical-records"),
        ("GET", "/api/v1/review/pending"),
        ("GET", "/api/v1/correction-logs/export/retraining")
    ]

    for method, path in routes_to_test:
        if method == "GET":
            response = unauthed_client.get(path)
        elif method == "POST":
            if "upload" in path:
                response = unauthed_client.post(path, files={"file": ("test.pdf", b"dummy content", "application/pdf")})
            else:
                response = unauthed_client.post(path)
                
        assert response.status_code == 401, f"Expected 401 Unauthorized for {method} {path}, got {response.status_code} - response: {response.text}"

def test_rbac_allows_hospital_admin_on_canonical_records(client: TestClient):
    """
    Ensure that a user with a valid role (e.g. hospital_admin) gets 200 OK 
    when hitting /api/v1/canonical-records, verifying the RBAC mapping is correct.
    """
    response = client.get("/api/v1/canonical-records")
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code} - {response.text}"
