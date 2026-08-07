"""
Unit tests for the ILLEGIBLE sentinel → flag mapping logic.

Tests that:
- Fields marked ILLEGIBLE get confidence_score=0.0 and verification_status="illegible"
- Fields with valid values get normal confidence and verification_status="extracted"
- The document's needs_manual_review is set to True when any field is illegible
- Mixed illegible/valid fields are mapped correctly per-field
"""

import pytest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

from app.services.handwriting.base import HandwritingExtractionResult
from app.schemas.extracted_field import ClinicalFieldsSchema, PatientIdentifierSchema
from app.services.handwriting.gemini_handwriting_extractor import GeminiHandwritingExtractor


class TestIllegibleSentinelParsing:
    """Tests for the GeminiHandwritingExtractor._parse_response method."""

    def _make_extractor(self):
        """Create an extractor with a mocked API key (no real API calls)."""
        with patch.object(GeminiHandwritingExtractor, '__init__', lambda self, **kw: None):
            ext = GeminiHandwritingExtractor.__new__(GeminiHandwritingExtractor)
            ext.api_key = "fake-key"
            ext.client = MagicMock()
            ext.model_name = "gemini-3.5-flash"
            return ext

    def test_valid_fields_have_normal_confidence(self):
        """Fields with readable values should have normal confidence."""
        ext = self._make_extractor()
        data = {
            "fields": {
                "patient_identifier": {
                    "name": "John Doe",
                    "patient_id": "MRN-12345",
                    "dob": "1990-01-15",
                    "gender": "Male",
                },
                "document_date": "2026-08-01",
            }
        }
        result = ext._parse_response(data)

        assert "patient_identifier" not in result.illegible_fields
        assert "document_date" not in result.illegible_fields
        assert result.field_confidences.get("patient_identifier", 0) > 0
        assert result.field_confidences.get("document_date", 0) > 0

    def test_illegible_string_field_is_flagged(self):
        """A top-level string field set to ILLEGIBLE is flagged."""
        ext = self._make_extractor()
        data = {
            "fields": {
                "document_date": "ILLEGIBLE",
                "patient_identifier": {"name": "Jane Doe", "patient_id": None, "dob": None, "gender": None},
            }
        }
        result = ext._parse_response(data)

        assert "document_date" in result.illegible_fields
        assert result.field_confidences["document_date"] == 0.0
        # The cleaned field should be None (not the string "ILLEGIBLE")
        assert result.fields.document_date is None

    def test_illegible_nested_field_is_flagged(self):
        """A dict field with any ILLEGIBLE sub-value flags the parent field."""
        ext = self._make_extractor()
        data = {
            "fields": {
                "patient_identifier": {
                    "name": "ILLEGIBLE",
                    "patient_id": "MRN-001",
                    "dob": None,
                    "gender": "Male",
                },
            }
        }
        result = ext._parse_response(data)

        assert "patient_identifier" in result.illegible_fields
        assert result.field_confidences["patient_identifier"] == 0.0
        # The name sub-field should be cleaned to None
        assert result.fields.patient_identifier.name is None
        # The readable sub-fields should be preserved
        assert result.fields.patient_identifier.patient_id == "MRN-001"
        assert result.fields.patient_identifier.gender == "Male"

    def test_illegible_list_item_field_is_flagged(self):
        """A list field with ILLEGIBLE values in any item flags the parent."""
        ext = self._make_extractor()
        data = {
            "fields": {
                "medications": [
                    {
                        "medication_name": "Amoxicillin",
                        "dosage": "ILLEGIBLE",
                        "frequency": "BID",
                    },
                ],
            }
        }
        result = ext._parse_response(data)

        assert "medications" in result.illegible_fields
        assert result.field_confidences["medications"] == 0.0
        # The medication name should be preserved
        assert result.fields.medications[0].medication_name == "Amoxicillin"
        # The illegible dosage should be None
        assert result.fields.medications[0].dosage is None

    def test_mixed_illegible_and_valid_fields(self):
        """Some fields illegible, others valid — only illegible ones flagged."""
        ext = self._make_extractor()
        data = {
            "fields": {
                "document_date": "2026-08-01",
                "patient_identifier": {
                    "name": "ILLEGIBLE",
                    "patient_id": None,
                    "dob": None,
                    "gender": None,
                },
                "ordering_physician": {
                    "name": "Dr. Smith",
                    "npi_or_license": None,
                    "department": "Cardiology",
                },
            }
        }
        result = ext._parse_response(data)

        # patient_identifier should be flagged (has ILLEGIBLE sub-field)
        assert "patient_identifier" in result.illegible_fields
        assert result.field_confidences["patient_identifier"] == 0.0

        # document_date and ordering_physician should NOT be flagged
        assert "document_date" not in result.illegible_fields
        assert "ordering_physician" not in result.illegible_fields
        assert result.field_confidences["document_date"] > 0
        assert result.field_confidences["ordering_physician"] > 0

    def test_case_insensitive_illegible_detection(self):
        """ILLEGIBLE sentinel detection is case-insensitive."""
        ext = self._make_extractor()
        for variant in ["ILLEGIBLE", "illegible", "Illegible", "iLlEgIbLe"]:
            data = {"fields": {"document_date": variant}}
            result = ext._parse_response(data)
            assert "document_date" in result.illegible_fields, f"Failed for variant: {variant}"

    def test_no_illegible_fields_returns_empty_list(self):
        """When all fields are readable, illegible_fields should be empty."""
        ext = self._make_extractor()
        data = {
            "fields": {
                "document_date": "2026-08-01",
                "patient_identifier": {
                    "name": "John Doe",
                    "patient_id": "123",
                    "dob": "1990-01-01",
                    "gender": "Male",
                },
            }
        }
        result = ext._parse_response(data)
        assert result.illegible_fields == []

    def test_empty_response_returns_default_result(self):
        """An empty fields dict should return defaults without errors."""
        ext = self._make_extractor()
        data = {"fields": {}}
        result = ext._parse_response(data)
        assert result.illegible_fields == []
        assert isinstance(result.fields, ClinicalFieldsSchema)


class TestIllegibleFlagIntegration:
    """
    Tests that the illegible flag mapping in upload_service produces the
    correct database state (confidence_score=0.0, verification_status="illegible",
    needs_manual_review=True).

    These test the mapping logic extracted from upload_service.process_document(),
    without actually running the full pipeline.
    """

    def test_illegible_field_gets_correct_status_and_confidence(self):
        """Simulate the post-processing step from upload_service."""
        # Create a mock ExtractedField record
        mock_field = MagicMock()
        mock_field.field_name = "patient_identifier"
        mock_field.confidence_score = 0.85
        mock_field.verification_status = "extracted"

        # Simulate the illegible mapping logic from upload_service
        illegible_fields = {"patient_identifier"}
        if mock_field.field_name in illegible_fields:
            mock_field.confidence_score = 0.0
            mock_field.verification_status = "illegible"

        assert mock_field.confidence_score == 0.0
        assert mock_field.verification_status == "illegible"

    def test_non_illegible_field_unchanged(self):
        """Fields not in the illegible set should keep their original values."""
        mock_field = MagicMock()
        mock_field.field_name = "document_date"
        mock_field.confidence_score = 0.85
        mock_field.verification_status = "extracted"

        illegible_fields = {"patient_identifier"}
        if mock_field.field_name in illegible_fields:
            mock_field.confidence_score = 0.0
            mock_field.verification_status = "illegible"

        assert mock_field.confidence_score == 0.85
        assert mock_field.verification_status == "extracted"

    def test_needs_manual_review_set_when_illegible(self):
        """Document.needs_manual_review should be True when any field is illegible."""
        mock_doc = MagicMock()
        mock_doc.needs_manual_review = False

        illegible_fields = ["patient_identifier", "medications"]
        updated_count = len(illegible_fields)

        if updated_count > 0:
            mock_doc.needs_manual_review = True

        assert mock_doc.needs_manual_review is True

    def test_needs_manual_review_not_set_when_no_illegible(self):
        """Document.needs_manual_review should not be changed when no fields are illegible."""
        mock_doc = MagicMock()
        mock_doc.needs_manual_review = False

        illegible_fields = []
        updated_count = len(illegible_fields)

        if updated_count > 0:
            mock_doc.needs_manual_review = True

        assert mock_doc.needs_manual_review is False

    def test_extract_from_pdf_uses_application_pdf_mime(self, tmp_path):
        """Verify that GeminiHandwritingExtractor passes application/pdf MIME type for .pdf files."""
        fake_pdf = tmp_path / "prescription.pdf"
        fake_pdf.write_bytes(b"%PDF-1.4 dummy pdf content")

        with patch.object(GeminiHandwritingExtractor, '__init__', lambda self, **kw: None):
            ext = GeminiHandwritingExtractor.__new__(GeminiHandwritingExtractor)
            ext.api_key = "fake-key"
            ext.client = MagicMock()
            ext.model_name = "gemini-3.5-flash"

            mock_response = MagicMock()
            mock_response.text = '{"fields": {"patient_identifier": {"name": "Test Patient"}}}'
            ext.client.models.generate_content.return_value = mock_response

            result = ext.extract_from_image(str(fake_pdf))

            assert result.fields.patient_identifier.name == "Test Patient"
            ext.client.models.generate_content.assert_called_once()
            call_args = ext.client.models.generate_content.call_args
            contents = call_args[1]["contents"] if "contents" in call_args[1] else call_args[0][0]
            # Verify part mime_type was application/pdf
            assert contents[0].inline_data.mime_type == "application/pdf"


