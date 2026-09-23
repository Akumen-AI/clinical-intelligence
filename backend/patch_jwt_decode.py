import pytest
import os
from unittest.mock import patch

def setup_jwt_patch(monkeypatch):
    import app.core.security
    original_decode = app.core.security.jwt.decode

    def patched_decode(token, secret, algorithms=None, **kwargs):
        payload = original_decode(token, secret, algorithms=algorithms, **kwargs)
        
        test_name = os.environ.get("PYTEST_CURRENT_TEST", "")
        if "test_auth_hardening" in test_name:
            return payload

        # Auto-provision user
        user_id_str = payload.get("sub")
        if user_id_str:
            from tests.conftest import TestingSessionLocal
            from app.models.user import User, UserRole
            import uuid
            
            db = TestingSessionLocal()
            try:
                uid = uuid.UUID(user_id_str)
                existing = db.query(User).filter(User.id == uid).first()
                if not existing:
                    role_str = payload.get("role", "nurse")
                    email = payload.get("email", f"{role_str}@test.clinic.org")
                    try:
                        enum_role = UserRole(role_str.lower())
                    except ValueError:
                        enum_role = UserRole.NURSE
                    u = User(id=uid, email=email, role=enum_role)
                    u.patient_access = payload.get("patient_access", [])
                    u.department_access = payload.get("department_access", [])
                    db.add(u)
                    db.commit()
            except Exception:
                db.rollback()
            finally:
                db.close()
                
        return payload

    monkeypatch.setattr(app.core.security.jwt, "decode", patched_decode)

