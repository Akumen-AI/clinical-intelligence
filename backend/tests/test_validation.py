import io
import pytest
from PIL import Image
from pypdf import PdfWriter

# Helper generators for test files
def make_valid_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

def make_encrypted_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.encrypt("user_pass", "owner_pass")
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

def make_valid_png_bytes() -> bytes:
    img = Image.new("RGB", (50, 50), color="green")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def make_valid_tiff_bytes() -> bytes:
    img = Image.new("RGB", (50, 50), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="TIFF")
    return buf.getvalue()

# Test cases
def test_valid_pdf_upload(client):
    content = make_valid_pdf_bytes()
    files = [("files", ("report.pdf", io.BytesIO(content), "application/pdf"))]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["accepted_count"] == 1
    assert data["accepted"][0]["filename"] == "report.pdf"
    assert data["accepted"][0]["status"] == "QUEUED"
    assert data["accepted"][0]["filetype"] == "pdf"

def test_valid_png_upload(client):
    content = make_valid_png_bytes()
    files = [("files", ("lab_results.png", io.BytesIO(content), "image/png"))]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["accepted"][0]["filename"] == "lab_results.png"
    assert data["accepted"][0]["status"] == "QUEUED"
    assert data["accepted"][0]["filetype"] == "png"

def test_valid_tiff_upload(client):
    content = make_valid_tiff_bytes()
    files = [("files", ("mri_scan.tiff", io.BytesIO(content), "image/tiff"))]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["accepted"][0]["filename"] == "mri_scan.tiff"
    assert data["accepted"][0]["status"] == "QUEUED"
    assert data["accepted"][0]["filetype"] == "tiff"

def test_corrupted_pdf_rejected(client):
    corrupted_content = b"%PDF-1.4 Invalid garbage content not a real pdf"
    files = [("files", ("broken.pdf", io.BytesIO(corrupted_content), "application/pdf"))]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded PDF is corrupted or unreadable."

def test_encrypted_pdf_rejected(client):
    encrypted_content = make_encrypted_pdf_bytes()
    files = [("files", ("protected.pdf", io.BytesIO(encrypted_content), "application/pdf"))]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded PDF is corrupted or unreadable."

def test_corrupted_png_rejected(client):
    corrupted_png = b"\x89PNG\r\n\x1a\nCorrupted image header bytes"
    files = [("files", ("bad_image.png", io.BytesIO(corrupted_png), "image/png"))]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded image could not be processed."

def test_zero_byte_empty_file_rejected(client):
    files = [("files", ("empty.pdf", io.BytesIO(b""), "application/pdf"))]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "The uploaded file is empty."

def test_docx_upload_rejected(client):
    files = [("files", ("document.docx", io.BytesIO(b"PK\x03\x04..."), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "This file type is not supported. Upload PDF, JPG, PNG or TIFF."

def test_zip_upload_rejected(client):
    files = [("files", ("archive.zip", io.BytesIO(b"PK\x03\x04zipdata"), "application/zip"))]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "This file type is not supported. Upload PDF, JPG, PNG or TIFF."

def test_oversized_file_rejected(client):
    large_bytes = b"A" * (20 * 1024 * 1024 + 100 * 1024)
    files = [("files", ("large_scan.pdf", io.BytesIO(large_bytes), "application/pdf"))]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert response.json()["detail"] == "File exceeds maximum upload size."

def test_multiple_upload_mixed_valid_and_invalid(client):
    pdf_valid = ("files", ("valid1.pdf", io.BytesIO(make_valid_pdf_bytes()), "application/pdf"))
    png_valid = ("files", ("valid2.png", io.BytesIO(make_valid_png_bytes()), "image/png"))
    docx_invalid = ("files", ("invalid.docx", io.BytesIO(b"docx content"), "application/docx"))
    corrupted_pdf = ("files", ("broken.pdf", io.BytesIO(b"%PDF corrupted"), "application/pdf"))

    response = client.post("/api/v1/documents/upload", files=[pdf_valid, png_valid, docx_invalid, corrupted_pdf])
    assert response.status_code == 201
    summary = response.json()
    assert summary["total_uploaded"] == 4
    assert summary["accepted_count"] == 2
    assert summary["rejected_count"] == 2
    assert len(summary["accepted"]) == 2
    assert len(summary["rejected"]) == 2

    rejected_names = [item["filename"] for item in summary["rejected"]]
    assert "invalid.docx" in rejected_names
    assert "broken.pdf" in rejected_names

def test_upload_logs_audit_trail(client, client_as):
    client.post("/api/v1/documents/upload", files=[("files", ("good.png", io.BytesIO(make_valid_png_bytes()), "image/png"))])
    client.post("/api/v1/documents/upload", files=[("files", ("bad.docx", io.BytesIO(b"data"), "application/docx"))])

    comp_client = client_as("compliance")
    response = comp_client.get("/api/v1/documents/upload-logs")
    assert response.status_code == 200
    logs = response.json()
    assert len(logs) >= 2
    statuses = [log["status"] for log in logs]
    assert "ACCEPTED" in statuses
    assert "REJECTED" in statuses
