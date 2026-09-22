import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User, UserRole
from app.models.refresh_token import RefreshToken
import uuid
import time
from app.core.security import create_access_token

def test_login_rate_limiting(client_as):
    c = TestClient(app)
    # Clear rate limits for the test by resetting the dict if needed, or just spam different IPs.
    # But since we use the same IP, 5 attempts should trigger it.
    for i in range(5):
        resp = c.post("/api/v1/auth/login", json={"email": "wrong@test.com", "password": "wrong"})
        assert resp.status_code in [401, 429]
    
    # 6th attempt should be 429
    resp = c.post("/api/v1/auth/login", json={"email": "wrong@test.com", "password": "wrong"})
    assert resp.status_code == 429

def test_role_change_reflected_immediately(client_as, db_session):
    # Setup user
    c = client_as("nurse")
    
    # Nurse tries to access dashboard export, should fail
    resp = c.get("/api/v1/documents/config/watched-folder")
    assert resp.status_code == 403
    
    # Now change role in DB to hospital_admin
    user_email = "nurse@test.clinic.org"
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == user_email).first()
    user.role = UserRole.HOSPITAL_ADMIN
    db.commit()
    db.close()
    
    # Same client (same token) makes request, should now succeed because DB is re-queried
    resp = c.get("/api/v1/documents/config/watched-folder")
    assert resp.status_code == 200

def test_revoked_user_rejected(client_as):
    c = client_as("nurse")
    resp = c.get("/api/v1/auth/me")
    assert resp.status_code == 200
    
    user_email = "nurse@test.clinic.org"
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    user = db.query(User).filter(User.email == user_email).first()
    db.delete(user)
    db.commit()
    db.close()
    
    # User no longer in DB, should be 401
    resp = c.get("/api/v1/auth/me")
    assert resp.status_code == 401

def test_query_parameter_bearer_token_rejected(client):
    # Create a valid token
    token = create_access_token({"sub": str(uuid.uuid4())})
    c = TestClient(app)
    # Don't set header or cookie, use query param
    resp = c.get("/api/v1/auth/me?token=" + token)
    assert resp.status_code == 401

def test_refresh_token_rotation_and_reuse():
    # Setup user
    user_id = uuid.uuid4()
    from conftest import TestingSessionLocal
    db = TestingSessionLocal()
    user = User(id=user_id, email="test_refresh@clinic.org", role=UserRole.NURSE)
    db.add(user)
    from app.models.refresh_token import RefreshToken
    from datetime import datetime, timezone, timedelta
    jti = uuid.uuid4().hex
    rt = RefreshToken(user_id=user_id, token_jti=jti, expires_at=datetime.now(timezone.utc) + timedelta(days=1))
    db.add(rt)
    db.commit()
    db.close()
    
    from app.core.security import create_refresh_token
    token, _ = create_refresh_token({"sub": str(user_id)})
    # override the token's jti manually to match the DB
    from jose import jwt
    from app.core.security import SECRET_KEY, ALGORITHM
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    payload["jti"] = jti
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    c = TestClient(app)
    c.cookies.set("refresh_token", token)
    
    # 1. Successful refresh
    resp = c.post("/api/v1/auth/refresh")
    assert resp.status_code == 200
    
    # The old token should now be revoked in DB.
    # 2. Reuse the old token
    resp = c.post("/api/v1/auth/refresh")
    assert resp.status_code == 401
    assert "revoked" in resp.json()["detail"].lower()
