import pytest
from fastapi.testclient import TestClient
from app.main import app

def test_upload():
    client = TestClient(app)
    import io
    from tests.test_upload import make_valid_pdf_bytes
    file_content = make_valid_pdf_bytes()
    files = [
        ("files", ("patient_report.pdf", io.BytesIO(file_content), "application/pdf"))
    ]
    response = client.post("/api/v1/documents/upload", files=files)
    print("STATUS", response.status_code)
    print("CONTENT", response.json())

test_upload()
