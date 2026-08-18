import os
import sys
import uuid
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure backend directory is on sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.database import Base, get_db
from app.main import app
from app.models.document import Document, DocumentStatus
from app.models.pending_review import PendingReview, ReviewStatus, SystemConfig
from app.services.confidence_router import (
    route_extraction_result,
    get_confidence_threshold,
    set_confidence_threshold,
    RoutingResult,
)
from app.services import canonical_record_service

from tests.conftest import TestingSessionLocal, engine


@pytest.fixture(autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Create test parent document to satisfy foreign keys
    test_doc = db.query(Document).filter(Document.document_id == "test-doc-123").first()
    if not test_doc:
        test_doc = Document(
            document_id="test-doc-123",
            filename="test.pdf",
            raw_uri="/uploads/test.pdf",
            filetype="pdf",
            status=DocumentStatus.EXTRACTED.value,
        )
        db.add(test_doc)
        db.commit()
    db.close()

    yield

    db = TestingSessionLocal()
    db.query(PendingReview).delete()
    db.query(SystemConfig).delete()
    db.commit()
    db.close()




def test_all_fields_above_threshold():
    """All fields above default threshold (0.80) -> all routed to canonical, 0 in pending_review."""
    db = TestingSessionLocal()
    extraction_result = {
        "document_id": "test-doc-123",
        "fields": {
            "patient_id": {"value": "PAT-999", "confidence": 0.95},
            "document_date": {"value": "2026-08-01", "confidence": 0.85},
            "diagnosis": {"value": "Hypertension", "confidence": 0.90},
        },
    }

    with patch.object(canonical_record_service, "upsert_field") as mock_upsert:
        res: RoutingResult = route_extraction_result(extraction_result, db=db)

        assert len(res.routed_to_canonical) == 3
        assert len(res.routed_to_review) == 0
        assert mock_upsert.call_count == 3

    pending_count = db.query(PendingReview).filter(PendingReview.document_id == "test-doc-123").count()
    assert pending_count == 0
    db.close()


def test_all_fields_below_threshold():
    """All fields below default threshold (0.80) -> all in pending_review."""
    db = TestingSessionLocal()
    extraction_result = {
        "document_id": "test-doc-123",
        "fields": {
            "symptoms": {"value": "Headache", "confidence": 0.40},
            "diagnosis": {"value": "Migraine", "confidence": 0.60},
            "vitals": {"value": "BP 120/80", "confidence": 0.75},
        },
    }

    with patch.object(canonical_record_service, "upsert_field") as mock_upsert:
        res: RoutingResult = route_extraction_result(extraction_result, db=db)

        assert len(res.routed_to_canonical) == 0
        assert len(res.routed_to_review) == 3
        assert mock_upsert.call_count == 0

    pending = db.query(PendingReview).filter(PendingReview.document_id == "test-doc-123").all()
    assert len(pending) == 3
    for p in pending:
        assert p.status == ReviewStatus.PENDING
    db.close()


def test_mixed_fields_split():
    """Mixed confidence scores -> correct split between canonical and review queue."""
    db = TestingSessionLocal()
    extraction_result = {
        "document_id": "test-doc-123",
        "fields": {
            "patient_id": {"value": "PAT-100", "confidence": 0.92},
            "diagnosis": {"value": "Diabetes", "confidence": 0.61},
            "vitals": {"value": "HR 72", "confidence": 0.82},
        },
    }

    with patch.object(canonical_record_service, "upsert_field") as mock_upsert:
        res: RoutingResult = route_extraction_result(extraction_result, db=db)

        assert res.routed_to_canonical == ["patient_id", "vitals"]
        assert res.routed_to_review == ["diagnosis"]
        assert mock_upsert.call_count == 2

    pending = db.query(PendingReview).filter(PendingReview.document_id == "test-doc-123").all()
    assert len(pending) == 1
    assert pending[0].field_name == "diagnosis"
    db.close()


def test_boundary_exact_threshold():
    """Boundary test: confidence exactly equal to threshold -> routed to canonical (inclusive >=)."""
    db = TestingSessionLocal()
    extraction_result = {
        "document_id": "test-doc-123",
        "fields": {
            "exact_boundary_field": {"value": "Boundary Value", "confidence": 0.80},
        },
    }

    with patch.object(canonical_record_service, "upsert_field") as mock_upsert:
        res: RoutingResult = route_extraction_result(extraction_result, db=db)

        assert res.routed_to_canonical == ["exact_boundary_field"]
        assert len(res.routed_to_review) == 0
        mock_upsert.assert_called_once()

    pending_count = db.query(PendingReview).filter(PendingReview.document_id == "test-doc-123").count()
    assert pending_count == 0
    db.close()


def test_threshold_zero_all_to_canonical():
    """When threshold = 0.01 (or set to low near 0), all non-negative fields go to canonical."""
    db = TestingSessionLocal()
    set_confidence_threshold(0.01, db=db)

    extraction_result = {
        "document_id": "test-doc-123",
        "fields": {
            "low_field_1": {"value": "val1", "confidence": 0.02},
            "low_field_2": {"value": "val2", "confidence": 0.10},
        },
    }

    with patch.object(canonical_record_service, "upsert_field") as mock_upsert:
        res: RoutingResult = route_extraction_result(extraction_result, db=db)

        assert len(res.routed_to_canonical) == 2
        assert len(res.routed_to_review) == 0
    db.close()


def test_threshold_one_all_to_review_except_exact_one():
    """When threshold = 1.0, fields < 1.0 go to review, exact 1.0 goes to canonical."""
    db = TestingSessionLocal()
    set_confidence_threshold(1.0, db=db)

    extraction_result = {
        "document_id": "test-doc-123",
        "fields": {
            "high_field": {"value": "val1", "confidence": 0.99},
            "perfect_field": {"value": "val2", "confidence": 1.00},
        },
    }

    with patch.object(canonical_record_service, "upsert_field") as mock_upsert:
        res: RoutingResult = route_extraction_result(extraction_result, db=db)

        assert res.routed_to_canonical == ["perfect_field"]
        assert res.routed_to_review == ["high_field"]
    db.close()


def test_get_pending_reviews_endpoint(client):
    """GET /api/v1/review/pending returns only PENDING records (not APPROVED or REJECTED)."""
    db = TestingSessionLocal()
    rec1 = PendingReview(
        id="rev-1",
        document_id="test-doc-123",
        field_name="diagnosis",
        extracted_value="Flu",
        confidence_score=0.65,
        status=ReviewStatus.PENDING,
    )
    rec2 = PendingReview(
        id="rev-2",
        document_id="test-doc-123",
        field_name="vitals",
        extracted_value="HR 80",
        confidence_score=0.55,
        status=ReviewStatus.APPROVED,
    )
    rec3 = PendingReview(
        id="rev-3",
        document_id="test-doc-123",
        field_name="symptoms",
        extracted_value="Fever",
        confidence_score=0.45,
        status=ReviewStatus.REJECTED,
    )
    db.add_all([rec1, rec2, rec3])
    db.commit()
    db.close()

    response = client.get("/api/v1/review/pending")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == "rev-1"
    assert data["items"][0]["status"] == "PENDING"


def test_patch_review_approve_and_reject(client):
    """PATCH /api/v1/review/pending/{id} approves or rejects items and invokes canonical record service on approve."""
    db = TestingSessionLocal()
    rec1 = PendingReview(
        id="rev-approve-1",
        document_id="test-doc-123",
        field_name="patient_id",
        extracted_value="PAT-12345",
        confidence_score=0.70,
        status=ReviewStatus.PENDING,
    )
    rec2 = PendingReview(
        id="rev-reject-1",
        document_id="test-doc-123",
        field_name="symptoms",
        extracted_value="Bad Text",
        confidence_score=0.30,
        status=ReviewStatus.PENDING,
    )
    db.add_all([rec1, rec2])
    db.commit()
    db.close()

    with patch.object(canonical_record_service, "upsert_field") as mock_upsert:
        # Approve rec1
        resp = client.patch(
            "/api/v1/review/pending/rev-approve-1",
            json={"action": "approve", "reviewer_id": "user-uuid-1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "APPROVED"
        assert data["reviewer_id"] == "user-uuid-1"
        mock_upsert.assert_called_once_with(
            document_id="test-doc-123",
            field_name="patient_id",
            value="PAT-12345",
            confidence=0.70,
            human_verified=True,
            db=pytest.any if hasattr(pytest, 'any') else mock_upsert.call_args[1]['db'],
        )

        # Reject rec2
        resp = client.patch(
            "/api/v1/review/pending/rev-reject-1",
            json={"action": "reject", "reviewer_id": "user-uuid-2"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "REJECTED"
        assert data["reviewer_id"] == "user-uuid-2"


def test_get_and_put_threshold_config_endpoints(client):
    """GET and PUT /api/v1/review/config/threshold work correctly."""
    # GET threshold (default env)
    resp = client.get("/api/v1/review/config/threshold")
    assert resp.status_code == 200
    data = resp.json()
    assert "threshold" in data
    assert data["source"] in ["env", "db"]

    # PUT threshold to 0.75
    resp = client.put(
        "/api/v1/review/config/threshold",
        json={"threshold": 0.75},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["threshold"] == 0.75
    assert data["source"] == "db"

    # GET threshold again -> returns 0.75 from db
    resp = client.get("/api/v1/review/config/threshold")
    assert resp.status_code == 200
    assert resp.json()["threshold"] == 0.75

    # Invalid threshold -> 422/400 validation error
    resp = client.put(
        "/api/v1/review/config/threshold",
        json={"threshold": 1.5},
    )
    assert resp.status_code in [400, 422]
