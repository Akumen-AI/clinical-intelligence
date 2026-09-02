import asyncio
from app.core.security import create_access_token, get_current_user
from fastapi.security import HTTPAuthorizationCredentials
import uuid

async def test():
    token = create_access_token({"sub": str(uuid.uuid4()), "role": "hospital_admin", "email": "test@clinic.org"})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    user = await get_current_user(creds)
    print("USER ROLE:", repr(user.role))
    
    from app.core.rbac import RBAC_MATRIX
    allowed = RBAC_MATRIX["/api/v1/patients"]
    print("ALLOWED:", allowed)
    print("IN ALLOWED:", user.role in allowed)

asyncio.run(test())
