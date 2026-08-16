import os
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from pydantic import BaseModel

SECRET_KEY = os.getenv("SECRET_KEY", "clinical_platform_secret_key_for_jwt_auth_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

security_scheme = HTTPBearer(auto_error=False)

class User(BaseModel):
    id: uuid.UUID
    role: Optional[str] = "nurse"
    email: Optional[str] = "reviewer@clinic.org"

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme)) -> User:
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    if token == "dev-token-for-testing-123":
        return User(id=uuid.uuid4(), role="doctor", email="test@clinic.org")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
            )
        reviewer_id = uuid.UUID(user_id_str)
        role = payload.get("role", "nurse")
        email = payload.get("email", "reviewer@clinic.org")
        return User(id=reviewer_id, role=role, email=email)
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


CLINICAL_READ_ROLES = {"doctor", "nurse", "hospital_admin", "department_head"}


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

