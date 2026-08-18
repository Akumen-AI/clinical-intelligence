import io
import pytest
from PIL import Image
from pypdf import PdfWriter
import time
from tests.conftest import override_get_db

def wait_for_document_processing(client, doc_id: str, timeout: int = 5):
    """Helper to poll document status until it is no longer queued."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        resp = client.get(f"/api/v1/documents/{doc_id}/status")
        if resp.status_code == 200:
            status_data = resp.json()
            if status_data["status"] != "QUEUED":
                return status_data
        time.time()
        time.sleep(0.5)
    raise TimeoutError(f"Document {doc_id} processing timed out.")

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
    assert data["accepted_count"] == 1
    assert data["accepted"][0]["filename"] == "patient_report.pdf"
    assert data["accepted"][0]["status"] == "QUEUED"
    assert data["accepted"][0]["filetype"] == "pdf"
    assert "document_id" in data["accepted"][0]

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
        assert item["status"] == "QUEUED"
        assert item["document_id"] is not None

def test_get_all_documents(client):
    file_content = make_valid_pdf_bytes()
    files = [("files", ("blood_work.pdf", io.BytesIO(file_content), "application/pdf"))]
    client.post("/api/v1/documents/upload", files=files)

    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) >= 1
    # We might not know which document is which, but at least one was queued/classified
    assert any(d["filename"] == "blood_work.pdf" for d in docs)

def test_get_document_status(client):
    file_content = make_valid_pdf_bytes()
    files = [("files", ("blood_work.pdf", io.BytesIO(file_content), "application/pdf"))]
    upload_resp = client.post("/api/v1/documents/upload", files=files)
    doc_id = upload_resp.json()["accepted"][0]["document_id"]

    status_data = wait_for_document_processing(client, doc_id)
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
    assert data["accepted_count"] == 1
    doc_id = data["accepted"][0]["document_id"]

    # Wait for processing to finish
    wait_for_document_processing(client, doc_id)

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

def test_upload_path_traversal(client):
    file_content = make_valid_pdf_bytes()
    # Attempt path traversal
    files = [
        ("files", ("../../../../tmp/evil.pdf", io.BytesIO(file_content), "application/pdf"))
    ]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    data = response.json()
    assert data["accepted_count"] == 1
    doc_id = data["accepted"][0]["document_id"]

    db = next(override_get_db())
    from app.services import upload_service
    doc = upload_service.get_document_by_id(db, doc_id)
    assert doc is not None
    # Verify that the filename was sanitized in the stored URI
    assert doc.raw_uri.startswith("uploads/")
    assert doc.raw_uri.endswith("evil.pdf")

def test_invalid_document_type_forces_manual_review(client, mocker):
    file_content = make_valid_pdf_bytes()
    
    # Mock the classifier to return a high-confidence but invalid document type
    mock_classifier = mocker.MagicMock()
    mock_result = mocker.MagicMock()
    mock_result.document_type = "Pizza Receipt"
    mock_result.confidence = 0.99
    mock_classifier.classify.return_value = mock_result
    mocker.patch("app.services.classification.factory.get_document_classifier", return_value=mock_classifier)
    
    # Skip actual text extraction for this test to speed it up and isolate it
    mocker.patch("app.services.text_extraction_service.extract_text", return_value="dummy text")
    # upload_service now uses extract_text_with_confidence for handwriting routing
    mocker.patch("app.services.text_extraction_service.extract_text_with_confidence", return_value=("dummy text", [0.95]))
    
    files = [("files", ("test.pdf", io.BytesIO(file_content), "application/pdf"))]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 201
    
    doc_id = response.json()["accepted"][0]["document_id"]
    status_data = wait_for_document_processing(client, doc_id)
    
    assert status_data["status"] in ("classified", "extracted", "unlinked")
    assert status_data["document_type"] == "Pizza Receipt"
    assert status_data["needs_manual_review"] == True

def test_delete_document_removes_files_from_uploads(client):
    import os
    file_content = make_valid_pdf_bytes()
    files = [("files", ("delete_test.pdf", io.BytesIO(file_content), "application/pdf"))]
    upload_resp = client.post("/api/v1/documents/upload", files=files)
    assert upload_resp.status_code == 201
    doc_id = upload_resp.json()["accepted"][0]["document_id"]

    wait_for_document_processing(client, doc_id)

    db = next(override_get_db())
    from app.services import upload_service
    doc = upload_service.get_document_by_id(db, doc_id)
    assert doc is not None

    backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    raw_path = os.path.join(backend_root, doc.raw_uri)
    assert os.path.exists(raw_path)

    # Now delete via API (same endpoint used by UI)
    delete_resp = client.delete(f"/api/v1/documents/{doc_id}")
    assert delete_resp.status_code == 200

    # Verify document is gone from DB
    deleted_doc = upload_service.get_document_by_id(db, doc_id)
    assert deleted_doc is None

    # Verify files are deleted from disk
    assert not os.path.exists(raw_path)
    if doc.processed_uri:
        proc_path = os.path.join(backend_root, doc.processed_uri)
        assert not os.path.exists(proc_path)

    # Verify no files with doc_id remain in uploads
    upload_dir = upload_service.UPLOAD_DIR
    matching = [f for f in os.listdir(upload_dir) if doc_id in f]
    assert len(matching) == 0

def test_delete_all_documents_cleans_uploads_folder(client):
    import os
    from app.services import upload_service
    file_content = make_valid_pdf_bytes()
    files1 = [("files", ("batch_test1.pdf", io.BytesIO(file_content), "application/pdf"))]
    files2 = [("files", ("batch_test2.pdf", io.BytesIO(file_content), "application/pdf"))]
    client.post("/api/v1/documents/upload", files=files1)
    client.post("/api/v1/documents/upload", files=files2)

    # Also put an orphaned file in upload directory
    orphan_path = os.path.join(upload_service.UPLOAD_DIR, "orphan_test_file.txt")
    with open(orphan_path, "w") as f:
        f.write("orphan")

    # Delete all documents via API
    resp = client.delete("/api/v1/documents")
    assert resp.status_code == 200

    # Verify uploads directory only has .gitkeep
    files_remaining = [f for f in os.listdir(upload_service.UPLOAD_DIR) if f != ".gitkeep"]
    assert len(files_remaining) == 0


