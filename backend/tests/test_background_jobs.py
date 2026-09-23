import pytest
from sqlalchemy.orm import Session
from uuid import uuid4

from app.models.document import Document, DocumentStatus
from app.tasks.document_tasks import process_document_task
from tests.conftest import TestingSessionLocal
from unittest.mock import patch, MagicMock
from celery.exceptions import Retry

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_process_document_task_success(db_session: Session, mocker):
    doc_id = str(uuid4())
    doc = Document(
        document_id=doc_id,
        filename="test.pdf",
        raw_uri="test.pdf",
        filetype="application/pdf",
        patient_id=None,
        status="QUEUED"
    )
    db_session.add(doc)
    db_session.commit()

    # Mock the actual heavy lifting
    mocker.patch("app.services.preprocessing_service.preprocess_document_file", return_value=("processed.pdf", 100))
    
    mock_classifier = mocker.MagicMock()
    mock_result = mocker.MagicMock()
    mock_result.document_type = "Prescription"
    mock_result.confidence = 0.99
    mock_classifier.classify.return_value = mock_result
    mocker.patch("app.services.classification.factory.get_document_classifier", return_value=mock_classifier)
    
    mocker.patch("app.services.text_extraction_service.extract_text_with_confidence", return_value=("Sample text", [0.9]))
    mocker.patch("app.services.field_extraction_service.extract_and_persist_fields")

    # Run the task directly (synchronously for testing via eager mode)
    process_document_task.delay(document_id=doc_id)

    db_session.refresh(doc)
    assert doc.status == DocumentStatus.EXTRACTED.value
    assert doc.document_type == "Prescription"
    assert doc.processed_uri == "processed.pdf"

def test_process_document_task_failure_triggers_retry(db_session: Session, mocker):
    doc_id = str(uuid4())
    doc = Document(
        document_id=doc_id,
        filename="test.pdf",
        raw_uri="test.pdf",
        filetype="application/pdf",
        patient_id=None,
        status="QUEUED"
    )
    db_session.add(doc)
    db_session.commit()

    # Make preprocessing throw a random exception to trigger retry
    mocker.patch("app.services.preprocessing_service.preprocess_document_file", side_effect=ValueError("Test transient error"))

    with pytest.raises(Retry):
        process_document_task.delay(document_id=doc_id)

    # Document gets marked as FAILED in the preprocessing catch block before it raises for retry
    db_session.refresh(doc)
    assert doc.status == DocumentStatus.FAILED.value
