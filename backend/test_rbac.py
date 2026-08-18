from fastapi.testclient import TestClient
from app.main import app
from app.database import SessionLocal
from app.models.user import User, UserRole
from app.models.audit_log import AuditLog
from sqlalchemy import text
import pytest

client = TestClient(app)

def setup_db():
    db = SessionLocal()
    # Ensure users exist
    roles = [UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN, UserRole.IT, UserRole.COMPLIANCE]
    for role in roles:
        email = f"{role.value}@test.com"
        if not db.query(User).filter_by(email=email).first():
            db.add(User(email=email, role=role))
    db.commit()
    db.close()

def get_token(role):
    # Actually, login might require password, let's just mock check_rbac or use the actual auth route if it's simple.
    # Wait, the auth route is app/api/v1/auth.py? Let's check how to authenticate.
    pass

if __name__ == "__main__":
    setup_db()
