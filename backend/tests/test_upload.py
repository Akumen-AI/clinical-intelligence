import io
import pytest
from PIL import Image
from pypdf import PdfWriter
from tests.conftest import override_get_db

def make_valid_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()

def make_valid_png_bytes() -> bytes:
    img = Image.new("RGB", (20, 20), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def make_valid_jpg_bytes() -> bytes:
    img = Image.new("RGB", (20, 20), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()

def make_valid_tiff_bytes() -> bytes:
    img = Image.new("RGB", (20, 20), color="yellow")
    buf = io.BytesIO()
    img.save(buf, format="TIFF")
    return buf.getvalue()

def test_root_health_check(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "Healthy"

def test_upload_single_valid_pdf(client):
    file_content = make_valid_pdf_bytes()
    files = [
        ("files", ("patient_report.pdf", io.BytesIO(file_content), "application/pdf"))
    ]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    assert data[0]["filename"] == "patient_report.pdf"
    assert data[0]["status"] == "classified"
    assert data[0]["filetype"] == "pdf"
    assert "document_id" in data[0]

def test_upload_invalid_extension_rejected(client):
    file_content = b"Mock docx file content"
    files = [
        ("files", ("resume.docx", io.BytesIO(file_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
    ]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert "This file type is not supported" in response.json()["detail"]

def test_upload_bulk_valid_files(client):
    file1 = ("files", ("lab_scan.png", io.BytesIO(make_valid_png_bytes()), "image/png"))
    file2 = ("files", ("prescription.jpg", io.BytesIO(make_valid_jpg_bytes()), "image/jpeg"))
    file3 = ("files", ("chest_xray.tiff", io.BytesIO(make_valid_tiff_bytes()), "image/tiff"))

    response = client.post("/api/v1/documents/upload", files=[file1, file2, file3])
    assert response.status_code == 201
    summary = response.json()
    assert summary["accepted_count"] == 3
    assert summary["rejected_count"] == 0
    for item in summary["accepted"]:
        assert item["status"] == "classified"
        assert item["document_id"] is not None

def test_get_all_documents(client):
    file_content = make_valid_pdf_bytes()
    files = [("files", ("blood_work.pdf", io.BytesIO(file_content), "application/pdf"))]
    client.post("/api/v1/documents/upload", files=files)

    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) >= 1
    assert docs[0]["filename"] == "blood_work.pdf"
    assert docs[0]["status"] == "classified"

def test_get_document_status(client):
    file_content = make_valid_pdf_bytes()
    files = [("files", ("blood_work.pdf", io.BytesIO(file_content), "application/pdf"))]
    upload_resp = client.post("/api/v1/documents/upload", files=files)
    doc_id = upload_resp.json()[0]["document_id"]

    response = client.get(f"/api/v1/documents/{doc_id}/status")
    assert response.status_code == 200
    status_data = response.json()
    assert status_data["document_id"] == doc_id
    assert status_data["status"] == "classified"

def test_upload_image_and_preprocess(client):
    import numpy as np
    import cv2
    import os
    from app.models.document import DocumentStatus

    # Create a simple 100x100 dummy image (white background with a black rectangle)
    img = np.ones((100, 100, 3), dtype=np.uint8) * 255
    cv2.rectangle(img, (20, 20), (80, 80), (0, 0, 0), -1)
    _, img_encoded = cv2.imencode('.png', img)
    image_bytes = img_encoded.tobytes()

    files = [
        ("files", ("test_image.png", io.BytesIO(image_bytes), "image/png"))
    ]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 1
    doc_id = data[0]["document_id"]

    # Verify database updates
    db = next(override_get_db())
    from app.services import upload_service
    doc = upload_service.get_document_by_id(db, doc_id)
    assert doc is not None
    assert doc.status == DocumentStatus.CLASSIFIED.value
    assert doc.processing_time_ms is not None
    assert doc.processing_time_ms >= 0
    assert doc.processed_uri is not None

    # Construct paths and check existence
    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    original_path = os.path.join(backend_root, doc.raw_uri)
    processed_path = os.path.join(backend_root, doc.processed_uri)

    assert os.path.exists(original_path)
    assert os.path.exists(processed_path)
    assert doc.raw_uri != doc.processed_uri

