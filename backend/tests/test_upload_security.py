import io
import pytest
from fastapi.testclient import TestClient
from app.main import app
from pypdf import PdfWriter

def make_valid_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

def test_unauthenticated_upload_rejected():
    client = TestClient(app)
    file_content = make_valid_pdf_bytes()
    files = [
        ("files", ("patient_report.pdf", io.BytesIO(file_content), "application/pdf"))
    ]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 401

def test_non_admin_delete_all_rejected(client_as):
    # Nurse is not a global admin
    client = client_as("nurse")
    response = client.delete("/api/v1/documents")
    assert response.status_code == 403

def test_unauthenticated_get_document_rejected():
    client = TestClient(app)
    response = client.get("/api/v1/documents")
    assert response.status_code == 401
