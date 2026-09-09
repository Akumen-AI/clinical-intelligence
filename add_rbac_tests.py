import os

tests = {
    "backend/tests/test_patient_rbac_endpoints.py": """
def test_notes_endpoints_denied_for_it(client_as):
    client = client_as("it")
    assert client.post("/api/v1/notes", json={"patient_id": "123", "content": "hello"}).status_code == 403
    assert client.get("/api/v1/notes/123").status_code == 403

def test_notes_post_denied_for_department_head(client_as):
    client = client_as("department_head")
    assert client.post("/api/v1/notes", json={"patient_id": "123", "content": "hello"}).status_code == 403
""",
    "backend/tests/test_deleted_routes_return_404.py": """import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_deleted_rag_routes_return_404(client_as):
    client = client_as("doctor")
    assert client.post("/api/v1/rag/query", json={"question": "hi"}).status_code == 404
    assert client.get("/api/v1/context-panel/123").status_code == 404
""",
    "backend/tests/test_dashboard.py": """
def test_dashboard_routes_denied_for_doctor(client_as):
    client = client_as("doctor")
    assert client.get("/api/v1/dashboards/department").status_code == 403
    assert client.get("/api/v1/dashboards/hospital").status_code == 403
""",
    "backend/tests/test_dashboard_export.py": """
def test_dashboard_export_denied_for_doctor(client_as):
    client = client_as("doctor")
    assert client.get("/api/v1/dashboards/hospital/export").status_code == 403
""",
    "backend/tests/test_dashboard_api.py": """
def test_dashboard_patient_denied_for_nurse(client_as):
    client = client_as("nurse")
    assert client.get("/api/v1/dashboards/patient/123").status_code == 403
""",
    "backend/tests/test_correction_logs.py": """
def test_correction_logs_denied_for_doctor(client_as):
    client = client_as("doctor")
    assert client.post("/api/v1/correction-logs/").status_code == 403
    assert client.get("/api/v1/correction-logs/123").status_code == 403
    assert client.get("/api/v1/correction-logs/document/doc123").status_code == 403
    assert client.get("/api/v1/correction-logs/patient/pat123").status_code == 403
""",
    "backend/tests/test_policy_chatbot_audit.py": """
def test_policy_chat_source_denied_for_it(client_as):
    client = client_as("it")
    assert client.get("/api/v1/policy-chat/source/somefile.pdf").status_code == 403
""",
    "backend/tests/api/test_audit_log.py": """
def test_get_patient_audit_logs_doctor_role_forbidden(client_as):
    client = client_as("doctor")
    assert client.get("/api/v1/audit-log/patient/123").status_code == 403
"""
}

for file_path, content in tests.items():
    mode = "a" if os.path.exists(file_path) else "w"
    with open(file_path, mode) as f:
        f.write(content)

print("Tests added.")
