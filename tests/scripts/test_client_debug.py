from fastapi.testclient import TestClient
from app.main import app
from app.core.security import create_access_token
import uuid
token = create_access_token({"sub": str(uuid.uuid4()), "role": "hospital_admin", "email": "test@clinic.org"})
client = TestClient(app)
client.headers.update({"Authorization": f"Bearer {token}"})
resp = client.post("/api/v1/patients", json={
    "mrn": "MRN-12345",
    "name": "John Doe",
    "dob": "1990-01-01",
    "sex": "Male"
})
print("STATUS:", resp.status_code)
print("BODY:", resp.json())
