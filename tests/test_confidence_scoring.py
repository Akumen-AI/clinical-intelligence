import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models.extraction_field import ExtractionField
from app.services.confidence_service import aggregate_field_confidence, get_field_status
from app.workers.ocr_tasks import extract_fields_task
from app.utils.confidence_spot_check import run_spot_check

# Use dedicated test database engine to prevent interfering with other test modules
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///./test_clinical_platform_confidence.db"
test_engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_database():
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def client():
    return TestClient(app)


def test_high_confidence_field_gets_auto_approved_status():
    char_confidences = [0.95, 0.92, 0.96, 0.94]
    confidence = aggregate_field_confidence(char_confidences)
    status = get_field_status(confidence, raw_value="P-1001")

    assert round(confidence, 2) == 0.94
    assert status == "auto_approved"


def test_low_confidence_field_gets_pending_review_status():
    char_confidences = [0.55, 0.60, 0.50, 0.45]
    confidence = aggregate_field_confidence(char_confidences)
    status = get_field_status(confidence, raw_value="DegradedText")

    assert round(confidence, 2) == 0.53
    assert status == "pending_review"


def test_no_detection_returns_zero_confidence():
    empty_ocr_data = []
    confidence = aggregate_field_confidence(empty_ocr_data)
    status = get_field_status(confidence, raw_value="")

    assert confidence == 0.0
    assert status == "illegible"


def test_confidence_persisted_to_db_not_transient():
    db = TestingSessionLocal()
    doc_id = str(uuid.uuid4())

    fields_config = [
        {
            "field_name": "patient_id",
            "raw_value": "P-9988",
            "char_confidences": [0.90, 0.92, 0.94],
        },
        {
            "field_name": "lab_result",
            "raw_value": "Low",
            "char_confidences": [0.40, 0.45],
        }
    ]

    extract_fields_task(document_id=doc_id, fields_config=fields_config, db=db)
    db.close()

    # Query using a fresh DB session to ensure data is persisted in database
    new_db = TestingSessionLocal()
    persisted_fields = new_db.query(ExtractionField).filter(
        ExtractionField.document_id == doc_id
    ).all()

    assert len(persisted_fields) == 2
    f1 = next(f for f in persisted_fields if f.field_name == "patient_id")
    f2 = next(f for f in persisted_fields if f.field_name == "lab_result")

    assert f1.confidence is not None
    assert f1.confidence > 0.85
    assert f1.status == "auto_approved"

    assert f2.confidence is not None
    assert f2.confidence < 0.75
    assert f2.status == "pending_review"
    new_db.close()


def test_spot_check_utility_runs_on_fixture_data():
    fixture_path = os.path.join("tests", "fixtures", "confidence_labels.json")
    if not os.path.exists(fixture_path):
        fixture_path = os.path.join(os.path.dirname(__file__), "fixtures", "confidence_labels.json")
    if not os.path.exists(fixture_path):
        fixture_path = os.path.join("backend", "tests", "fixtures", "confidence_labels.json")

    results = run_spot_check(fixture_path)
    assert "pass_rate" in results
    assert results["pass_rate"] == 1.0
    assert len(results["field_results"]) == 10
    assert "distribution_summary" in results


def test_api_returns_confidence_per_field(client):
    db = TestingSessionLocal()
    doc_id = str(uuid.uuid4())

    field_1 = ExtractionField(
        field_id=str(uuid.uuid4()),
        document_id=doc_id,
        field_name="patient_name",
        raw_value="Jane Doe",
        confidence=0.92,
        status="auto_approved"
    )
    field_2 = ExtractionField(
        field_id=str(uuid.uuid4()),
        document_id=doc_id,
        field_name="notes",
        raw_value="Unclear handwriting",
        confidence=0.55,
        status="pending_review"
    )

    db.add(field_1)
    db.add(field_2)
    db.commit()
    db.close()

    response = client.get(f"/documents/{doc_id}/fields")
    assert response.status_code == 200

    data = response.json()
    assert data["document_id"] == doc_id
    assert len(data["fields"]) == 2

    names = {f["field_name"]: f for f in data["fields"]}
    assert "patient_name" in names
    assert names["patient_name"]["confidence"] == 0.92
    assert names["patient_name"]["status"] == "auto_approved"

    assert "notes" in names
    assert names["notes"]["confidence"] == 0.55
    assert names["notes"]["status"] == "pending_review"


def test_confidence_summary_counts_are_accurate(client):
    db = TestingSessionLocal()
    doc_id = str(uuid.uuid4())

    # Add 3 auto_approved and 2 pending_review fields
    for i in range(3):
        db.add(ExtractionField(
            field_id=str(uuid.uuid4()),
            document_id=doc_id,
            field_name=f"auto_field_{i}",
            raw_value=f"val_{i}",
            confidence=0.85,
            status="auto_approved"
        ))
    for i in range(2):
        db.add(ExtractionField(
            field_id=str(uuid.uuid4()),
            document_id=doc_id,
            field_name=f"review_field_{i}",
            raw_value=f"val_{i}",
            confidence=0.60,
            status="pending_review"
        ))

    db.commit()
    db.close()

    response = client.get(f"/documents/{doc_id}/fields")
    assert response.status_code == 200

    summary = response.json()["confidence_summary"]
    assert summary["total_fields"] == 5
    assert summary["auto_approved"] == 3
    assert summary["pending_review"] == 2
    assert summary["mean_confidence"] == 0.75
