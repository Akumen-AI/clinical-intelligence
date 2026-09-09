from fastapi import FastAPI, Depends, Request
from fastapi.testclient import TestClient

app = FastAPI()

def check_rbac(request: Request):
    route = request.scope.get("route")
    return route.path if route else None

@app.post("/api/v1/patients/{patient_id}/ask", dependencies=[Depends(check_rbac)])
def ask(request: Request, patient_id: str):
    return {"path": request.scope.get("route").path}

client = TestClient(app)
resp = client.post("/api/v1/patients/123/ask")
print(resp.json())
