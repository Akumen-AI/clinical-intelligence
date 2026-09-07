import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.security import create_access_token
import uuid

async def run():
    comp_token = create_access_token({"sub": str(uuid.uuid4()), "role": "compliance", "email": "comp@clinic.org"})
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/api/v1/audit-log/patient/e2e_patient", headers={"Authorization": f"Bearer {comp_token}"})
        print("Status:", res.status_code)
        print("Body:", res.text)

asyncio.run(run())
