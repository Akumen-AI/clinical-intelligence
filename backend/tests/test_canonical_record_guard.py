"""Tests for the canonical-record write safety gate."""

import logging

import pytest

from app.models.extracted_field import ExtractedField
from app.models.canonical_patient_record import CanonicalPatientRecord
from app.services import canonical_record_service
from app.services.canonical_record_service import CanonicalWriteRejected
from tests.conftest import TestingSessionLocal


def test_high_confidence_extracted_field_passes_through():
    db = TestingSessionLocal()

    record = canonical_record_service.upsert_field(
        document_id="test-doc-123",
        field_name="patient_id",
        value="PAT-100",
        confidence=0.95,
        db=db,
    )

    assert record.value == "PAT-100"
    
    extracted = db.query(ExtractedField).filter(ExtractedField.field_id == record.source_field_id).first()
    assert extracted.verification_status == "auto_passed"
    db.close()


def test_low_confidence_write_is_blocked_and_logged(caplog):
    db = TestingSessionLocal()

    with caplog.at_level(logging.WARNING, logger="app.services.canonical_record_service"):
        with pytest.raises(CanonicalWriteRejected, match="below threshold"):
            canonical_record_service.upsert_field(
                document_id="test-doc-123",
                field_name="diagnosis",
                value="Uncertain diagnosis",
                confidence=0.30,
                db=db,
            )

    assert "Rejected canonical write" in caplog.text
    assert "diagnosis" in caplog.text
    assert (
        db.query(ExtractedField)
        .filter(
            ExtractedField.document_id == "test-doc-123",
            ExtractedField.field_name == "diagnosis",
        )
        .first()
        is None
    )
    db.close()


def test_failed_field_is_blocked_even_with_high_confidence(caplog):
    db = TestingSessionLocal()
    failed = ExtractedField(
        field_id="failed-field-1",
        document_id="test-doc-123",
        field_name="lab_result",
        raw_value="bad OCR",
        confidence_score=0.95,
        verification_status="failed",
    )
    db.add(failed)
    db.commit()

    with caplog.at_level(logging.WARNING, logger="app.services.canonical_record_service"):
        with pytest.raises(CanonicalWriteRejected, match="not writable"):
            canonical_record_service.upsert_field(
                document_id="test-doc-123",
                field_name="lab_result",
                value="should not commit",
                confidence=0.95,
                db=db,
            )

    db.refresh(failed)
    assert failed.verification_status == "failed"
    assert failed.verified_value is None
    assert "field status 'failed' is not writable" in caplog.text
    db.close()


def test_low_confidence_cannot_overwrite_existing_canonical_field():
    db = TestingSessionLocal()
    canonical = CanonicalPatientRecord(
        document_id="test-doc-123",
        field_name="patient_id",
        value="PAT-ORIGINAL",
        source_field_id="canonical-field-1",
    )
    db.add(canonical)
    db.commit()

    with pytest.raises(CanonicalWriteRejected, match="below threshold"):
        canonical_record_service.upsert_field(
            document_id="test-doc-123",
            field_name="patient_id",
            value="PAT-UNVERIFIED-OVERWRITE",
            confidence=0.10,
            db=db,
        )

    db.refresh(canonical)
    assert canonical.value == "PAT-ORIGINAL"
    db.close()


def test_human_verified_low_confidence_field_can_pass():
    db = TestingSessionLocal()

    record = canonical_record_service.upsert_field(
        document_id="test-doc-123",
        field_name="handwritten_note",
        value="Clinician confirmed",
        confidence=0.20,
        db=db,
        human_verified=True,
    )

    assert record.value == "Clinician confirmed"
    extracted = db.query(ExtractedField).filter(ExtractedField.field_id == record.source_field_id).first()
    assert extracted.verification_status == "human_verified"
    db.close()
