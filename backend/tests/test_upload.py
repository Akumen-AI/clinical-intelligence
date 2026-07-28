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
    assert data[0]["status"] == "new"
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
        assert item["status"] == "new"
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
    assert docs[0]["status"] == "new"

def test_get_document_status():
    file_content = b"%PDF-1.4 Test"
    files = [("files", ("blood_work.pdf", io.BytesIO(file_content), "application/pdf"))]
    upload_resp = client.post("/api/v1/documents/upload", files=files)
    doc_id = upload_resp.json()[0]["document_id"]

    response = client.get(f"/api/v1/documents/{doc_id}/status")
    assert response.status_code == 200
    status_data = response.json()
    assert status_data["document_id"] == doc_id
    assert status_data["status"] == "new"
