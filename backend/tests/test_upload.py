import io
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_clinical_platform.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

client = TestClient(app)

def test_root_health_check():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "Healthy"

def test_upload_single_valid_pdf():
    file_content = b"%PDF-1.4 Mock PDF clinical report"
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

def test_upload_invalid_extension_rejected():
    file_content = b"Mock docx file content"
    files = [
        ("files", ("resume.docx", io.BytesIO(file_content), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))
    ]
    response = client.post("/api/v1/documents/upload", files=files)
    assert response.status_code == 400
    assert "Unsupported file type '.docx'" in response.json()["detail"]

def test_upload_bulk_valid_files():
    file1 = ("files", ("lab_scan.png", io.BytesIO(b"PNG mock data"), "image/png"))
    file2 = ("files", ("prescription.jpg", io.BytesIO(b"JPEG mock data"), "image/jpeg"))
    file3 = ("files", ("chest_xray.tiff", io.BytesIO(b"TIFF mock data"), "image/tiff"))

    response = client.post("/api/v1/documents/upload", files=[file1, file2, file3])
    assert response.status_code == 201
    data = response.json()
    assert len(data) == 3
    for item in data:
        assert item["status"] == "classified"
        assert item["document_id"] is not None

def test_get_all_documents():
    # Upload first
    file_content = b"%PDF-1.4 Test"
    files = [("files", ("blood_work.pdf", io.BytesIO(file_content), "application/pdf"))]
    client.post("/api/v1/documents/upload", files=files)

    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    docs = response.json()
    assert len(docs) >= 1
    assert docs[0]["filename"] == "blood_work.pdf"
    assert docs[0]["status"] == "classified"

def test_get_document_status():
    file_content = b"%PDF-1.4 Test"
    files = [("files", ("blood_work.pdf", io.BytesIO(file_content), "application/pdf"))]
    upload_resp = client.post("/api/v1/documents/upload", files=files)
    doc_id = upload_resp.json()[0]["document_id"]

    response = client.get(f"/api/v1/documents/{doc_id}/status")
    assert response.status_code == 200
    status_data = response.json()
    assert status_data["document_id"] == doc_id
    assert status_data["status"] == "classified"

def test_upload_image_and_preprocess():
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

