import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from sqlalchemy.orm import Session
from app.database import SessionLocal, Base, engine
from app.models.user import User, UserRole
from app.core.security import get_password_hash

# IMPORTANT: These are synthetic demo accounts only! 
# Do not use these in a production environment.

import secrets
import string

def _generate_password(length=16):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))

DEMO_USERS = [
    {"email": "doctor@demo.com", "role": UserRole.DOCTOR, "password": _generate_password()},
    {"email": "nurse@demo.com", "role": UserRole.NURSE, "password": _generate_password()},
    {"email": "admin@demo.com", "role": UserRole.HOSPITAL_ADMIN, "password": _generate_password()},
    {"email": "head@demo.com", "role": UserRole.DEPARTMENT_HEAD, "password": _generate_password()},
    {"email": "it@demo.com", "role": UserRole.IT, "password": _generate_password()},
    {"email": "compliance@demo.com", "role": UserRole.COMPLIANCE, "password": _generate_password()},
]

def seed_users():
    db: Session = SessionLocal()
    try:
        for user_data in DEMO_USERS:
            existing_user = db.query(User).filter(User.email == user_data["email"]).first()
            if not existing_user:
                new_user = User(
                    email=user_data["email"],
                    role=user_data["role"],
                    password_hash=get_password_hash(user_data["password"])
                )
                db.add(new_user)
                print(f"Created demo user: {user_data['email']} with role {user_data['role'].value}. Password: {user_data['password']}")
            else:
                existing_user.password_hash = get_password_hash(user_data["password"])
                print(f"Updated password for demo user: {user_data['email']}. Password: {user_data['password']}")
        db.commit()
        print("Demo users seeded successfully.")
    except Exception as e:
        print(f"Error seeding users: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_users()
