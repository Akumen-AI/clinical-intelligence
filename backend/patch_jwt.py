import pytest
from unittest.mock import patch
from app.core import security
from app.models.user import User, UserRole
import uuid

original_create_access_token = security.create_access_token

def patched_create_access_token(data: dict, expires_delta=None):
    from tests.conftest import TestingSessionLocal
    user_id_str = data.get("sub")
    role_str = data.get("role", "nurse")
    email = data.get("email", f"{role_str}@test.clinic.org")
    
    if user_id_str:
        db = TestingSessionLocal()
        try:
            uid = uuid.UUID(user_id_str)
            existing = db.query(User).filter(User.id == uid).first()
            if not existing:
                try:
                    enum_role = UserRole(role_str.lower())
                except ValueError:
                    enum_role = UserRole.NURSE
                u = User(id=uid, email=email, role=enum_role)
                db.add(u)
                db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
            
    return original_create_access_token(data, expires_delta)

