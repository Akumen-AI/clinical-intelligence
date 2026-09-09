import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_rag_routes_denied_for_it(client_as):
    client = client_as("it")
    assert client.post("/api/v1/rag/query", json={"question": "hi"}).status_code == 403
    assert client.get("/api/v1/context-panel/123").status_code == 403
