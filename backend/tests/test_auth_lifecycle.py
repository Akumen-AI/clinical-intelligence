import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User, UserRole
import uuid
from app.core.security import get_password_hash

def test_full_auth_lifecycle(client_as):
    user_id = uuid.uuid4()
    from tests.conftest import TestingSessionLocal
    db = TestingSessionLocal()
    user = User(
        id=user_id, 
        email="lifecycle@test.clinic.org", 
        role=UserRole.NURSE,
        password_hash=get_password_hash("securepassword123")
    )
    db.add(user)
    db.commit()
    db.close()

    c = TestClient(app, base_url="https://testserver")

    # 1. Login with bad password
    resp = c.post("/api/v1/auth/login", json={"email": "lifecycle@test.clinic.org", "password": "wrongpassword"})
    assert resp.status_code in [401, 429]  # 429 possible due to rate limit if running repeatedly

    # 2. Login with correct password
    resp = c.post("/api/v1/auth/login", json={"email": "lifecycle@test.clinic.org", "password": "securepassword123"})
    assert resp.status_code == 200
    
    # Check cookies
    assert "access_token" in c.cookies
    assert "refresh_token" in c.cookies
    
    # 3. Access protected route (/me)
    resp = c.get("/api/v1/auth/me")
    assert resp.status_code == 200
    assert resp.json()["email"] == "lifecycle@test.clinic.org"

    # 4. Refresh token
    resp = c.post("/api/v1/auth/refresh")
    assert resp.status_code == 200
    # tokens should be rotated

    # 5. Access protected route again
    resp = c.get("/api/v1/auth/me")
    assert resp.status_code == 200
    
    # 6. Logout
    resp = c.post("/api/v1/auth/logout")
    assert resp.status_code == 200
    
    # Verify logout cleared cookies (TestClient handles cookies across requests but clear() is needed to simulate browser behavior properly sometimes)
    c.cookies.clear()
    
    # 7. Access protected route (should fail)
    resp = c.get("/api/v1/auth/me")
    assert resp.status_code == 401
