import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel
from app.models.user import UserRole

from passlib.context import CryptContext

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    if os.getenv("DEV_MODE", "").lower() == "true":
        SECRET_KEY = "clinical_platform_secret_key_for_jwt_auth_2026"
    else:
        raise ValueError("SECRET_KEY environment variable must be set unless DEV_MODE=true")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24
REFRESH_TOKEN_EXPIRE_DAYS = 7

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
security_scheme = HTTPBearer(auto_error=False)

class User(BaseModel):
    id: uuid.UUID
    role: Optional[UserRole] = UserRole.NURSE
    email: Optional[str] = "reviewer@clinic.org"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type", "access") != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
            )
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        reviewer_id = uuid.UUID(user_id_str)
        role_str = payload.get("role", "nurse")
        try:
            role = UserRole(role_str)
        except ValueError:
            role = UserRole.NURSE
        email = payload.get("email", "reviewer@clinic.org")
        return User(id=reviewer_id, role=role, email=email)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


CLINICAL_READ_ROLES = {UserRole.DOCTOR, UserRole.NURSE, UserRole.HOSPITAL_ADMIN, UserRole.DEPARTMENT_HEAD}


def require_clinical_read(current_user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency that gates any endpoint on clinical-read roles.
    Raises HTTP 403 for authenticated users whose role is not in CLINICAL_READ_ROLES.
    FR-20: access-scoped RAG responses.
    """
    if current_user.role not in CLINICAL_READ_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: insufficient role",
        )
    return current_user

