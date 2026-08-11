import uuid
from app.models.document import Document, DocumentStatus
from app.models.extracted_field import ExtractedField, VerificationStatus
from app.models.canonical_patient_record import CanonicalPatientRecord
from tests.conftest import TestingSessionLocal


def _seed_document_with_canonical_record(
    db,
    patient_id: str = "P001",
    document_type: str = "Lab Report",
    filename: str = "test_lab.pdf",
    date_val: str = "2024-01-15",
    status: str = DocumentStatus.COMMITTED.value,
):
    doc_id = str(uuid.uuid4())
    field_id = str(uuid.uuid4())

    doc = Document(
        document_id=doc_id,
        patient_id=patient_id,
        filename=filename,
        raw_uri=f"uploads/{filename}",
        filetype="pdf",
        status=status,
        document_type=document_type,
    )
    db.add(doc)

    field = ExtractedField(
        field_id=field_id,
        document_id=doc_id,
        field_name="document_date",
        raw_value=date_val,
        confidence_score=0.95,
        verification_status=VerificationStatus.AUTO_PASSED,
    )
    db.add(field)

    canonical = CanonicalPatientRecord(
        document_id=doc_id,
        field_name="document_date",
        value=date_val,
        source_field_id=field_id,
    )
    db.add(canonical)
    db.commit()

    return doc, field, canonical


def test_timeline_empty_returns_200_with_zero_events(client):
    response = client.get("/api/v1/timeline")
    assert response.status_code == 200
    data = response.json()
    assert data["total_events"] == 0
    assert data["events"] == []


def test_timeline_returns_committed_doc_in_chronological_order(client):
    db = TestingSessionLocal()
    try:
        _seed_document_with_canonical_record(
            db, filename="recent.pdf", date_val="2025-06-01"
        )
        _seed_document_with_canonical_record(
            db, filename="older.pdf", date_val="2024-01-15"
        )
    finally:
        db.close()

    response = client.get("/api/v1/timeline")
    assert response.status_code == 200
    data = response.json()
    assert data["total_events"] == 2
    assert data["events"][0]["event_date"] == "2024-01-15"
    assert data["events"][1]["event_date"] == "2025-06-01"
    assert "document_id" in data["events"][0]
    assert "document_id" in data["events"][1]


def test_timeline_entry_links_to_source_document(client):
    db = TestingSessionLocal()
    try:
        doc, _, _ = _seed_document_with_canonical_record(db)
        doc_id = doc.document_id
    finally:
        db.close()

    response = client.get("/api/v1/timeline")
    assert response.status_code == 200
    events = response.json()["events"]
    assert len(events) == 1
    assert events[0]["document_id"] == doc_id

    event_res = client.get(f"/api/v1/timeline/{doc_id}")
    assert event_res.status_code == 200
    assert event_res.json()["document_id"] == doc_id


def test_timeline_excludes_non_committed_documents(client):
    db = TestingSessionLocal()
    try:
        _seed_document_with_canonical_record(
            db, filename="committed.pdf", status=DocumentStatus.COMMITTED.value
        )
        _seed_document_with_canonical_record(
            db, filename="pending.pdf", status=DocumentStatus.PENDING_REVIEW.value
        )
    finally:
        db.close()

    response = client.get("/api/v1/timeline")
    assert response.status_code == 200
    data = response.json()
    assert data["total_events"] == 1
    assert data["events"][0]["filename"] == "committed.pdf"


def test_timeline_updates_when_new_verified_doc_added(client):
    db = TestingSessionLocal()
    try:
        _seed_document_with_canonical_record(
            db, filename="doc1.pdf", date_val="2024-01-01"
        )
    finally:
        db.close()

    res1 = client.get("/api/v1/timeline")
    assert res1.status_code == 200
    assert res1.json()["total_events"] == 1

    db2 = TestingSessionLocal()
    try:
        _seed_document_with_canonical_record(
            db2, filename="doc2.pdf", date_val="2024-06-01"
        )
    finally:
        db2.close()

    res2 = client.get("/api/v1/timeline")
    assert res2.status_code == 200
    assert res2.json()["total_events"] == 2
    assert res2.json()["events"][0]["event_date"] == "2024-01-01"
    assert res2.json()["events"][1]["event_date"] == "2024-06-01"


def test_timeline_filter_by_patient_id(client):
    db = TestingSessionLocal()
    try:
        doc1, _, _ = _seed_document_with_canonical_record(db, patient_id="P001")
        doc2, _, _ = _seed_document_with_canonical_record(db, patient_id="P002")
        doc1_id = doc1.document_id
    finally:
        db.close()

    response = client.get("/api/v1/timeline?patient_id=P001")
    assert response.status_code == 200
    data = response.json()
    assert data["total_events"] == 1
    assert data["events"][0]["document_id"] == doc1_id


def test_timeline_event_404_for_unknown_document(client):
    response = client.get("/api/v1/timeline/nonexistent-doc-id")
    assert response.status_code == 404
