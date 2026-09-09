from fastapi import FastAPI, Depends, Request, APIRouter
from fastapi.testclient import TestClient

app = FastAPI()
router = APIRouter(prefix="/patients")

def check_rbac(request: Request):
    route = request.scope.get("route")
    print("MATCHED ROUTE:", route.path if route else "None")

@router.post("/{patient_id}/ask")
def ask(request: Request, patient_id: str):
    return {"status": "ok"}

app.include_router(router, prefix="/api/v1", dependencies=[Depends(check_rbac)])

client = TestClient(app)
resp = client.post("/api/v1/patients/123/ask")
print(resp.json())
