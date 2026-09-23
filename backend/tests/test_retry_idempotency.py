import pytest
from sqlalchemy.orm import Session
from uuid import uuid4

from app.models.document import Document, DocumentStatus
from app.models.extracted_field import ExtractedField
from app.tasks.document_tasks import process_document_task
from tests.conftest import TestingSessionLocal
from unittest.mock import patch, MagicMock

@pytest.fixture
def db_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_process_document_idempotency(db_session: Session, mocker):
    doc_id = str(uuid4())
    doc = Document(
        document_id=doc_id,
        filename="test_retry.pdf",
        raw_uri="test_retry.pdf",
        filetype="application/pdf",
        patient_id=None,
        status="QUEUED"
    )
    db_session.add(doc)
    db_session.commit()

    # Mocks
    mocker.patch("app.services.preprocessing_service.preprocess_document_file", return_value=("processed.pdf", 100))
    
    mock_classifier = mocker.MagicMock()
    mock_result = mocker.MagicMock()
    mock_result.document_type = "Prescription"
    mock_result.confidence = 0.99
    mock_classifier.classify.return_value = mock_result
    mocker.patch("app.services.classification.factory.get_document_classifier", return_value=mock_classifier)
    
    # Mock text extraction
    mocker.patch("app.services.text_extraction_service.extract_text_with_confidence", return_value=("Sample text", [0.9]))
    
    # Run the task first time
    process_document_task.delay(document_id=doc_id)
    
    db_session.refresh(doc)
    assert doc.status == DocumentStatus.EXTRACTED.value
    
    first_run_id = doc.current_extraction_run_id
    
    fields_first_run = db_session.query(ExtractedField).filter(
        ExtractedField.document_id == doc_id,
        ExtractedField.extraction_run_id == first_run_id
    ).count()
    
    assert fields_first_run > 0
    
    # Run the task a SECOND time (retry idempotency)
    # Re-queue
    doc.status = DocumentStatus.QUEUED.value
    db_session.commit()
    
    process_document_task.delay(document_id=doc_id)
    
    db_session.refresh(doc)
    assert doc.status == DocumentStatus.EXTRACTED.value
    
    second_run_id = doc.current_extraction_run_id
    assert second_run_id != first_run_id
    
    fields_second_run = db_session.query(ExtractedField).filter(
        ExtractedField.document_id == doc_id,
        ExtractedField.extraction_run_id == second_run_id
    ).count()
    
    assert fields_second_run == fields_first_run
