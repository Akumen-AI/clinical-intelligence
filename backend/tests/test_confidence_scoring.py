"""
Story 2.3 — Field-Level Confidence Scoring Tests

Covers:
  AC-1: Every extracted field carries a confidence_score in [0.0, 1.0]
  AC-2: Score is persisted in the DB, not computed transiently
  AC-3: Spot-check against labeled sample (correct > 0.70, wrong < 0.50)

Plus unit-level coverage of all four ConfidenceEngine signals.
"""

import uuid
import statistics
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.models.document import Document, DocumentStatus
from app.models.extracted_field import ExtractedField
from app.services.confidence_engine import ConfidenceEngine
from app.services.extraction.rule_based_extractor import RuleBasedFieldExtractor
from tests.fixtures.labeled_sample import LABELED_SAMPLE
from tests.conftest import TestingSessionLocal


# ---------------------------------------------------------------------------
# Helper: score every sample through the engine
# ---------------------------------------------------------------------------
_engine = ConfidenceEngine()


def _score_sample(sample: dict) -> float:
    return _engine.score_field(
        field_name=sample["field_name"],
        raw_value=sample["raw_value"],
        ocr_word_confidences=sample["ocr_word_confidences"],
        layout_region=sample["layout_region"],
        document_type=sample["document_type"],
        field_map=sample.get("field_map"),
    )


# ===================================================================
# AC-3 SPOT-CHECK TESTS
# ===================================================================

class TestSpotCheckLabeledSample:
    """AC-3: Score distribution against labeled sample."""

    def test_labeled_sample_has_enough_examples(self):
        """Fixture must have >= 10 examples."""
        assert len(LABELED_SAMPLE) >= 10

    def test_every_sample_in_range(self):
        """AC-1: Every score is in [0.0, 1.0]."""
        for sample in LABELED_SAMPLE:
            score = _score_sample(sample)
            assert 0.0 <= score <= 1.0, (
                f"Score {score} out of range for {sample['field_name']} "
                f"(value={sample['raw_value']!r})"
            )

    def test_correct_extractions_have_high_mean_score(self):
        """AC-3: Mean confidence of correct extractions > 0.70."""
        correct_scores = [
            _score_sample(s) for s in LABELED_SAMPLE if s["ground_truth_correct"]
        ]
        assert len(correct_scores) > 0, "No correct samples in LABELED_SAMPLE"
        mean_correct = statistics.mean(correct_scores)
        assert mean_correct > 0.70, (
            f"Mean score of correct extractions ({mean_correct:.4f}) <= 0.70; "
            f"individual scores: {[round(s, 4) for s in correct_scores]}"
        )

    def test_wrong_extractions_have_low_mean_score(self):
        """AC-3: Mean confidence of wrong/null extractions < 0.50."""
        wrong_scores = [
            _score_sample(s) for s in LABELED_SAMPLE if not s["ground_truth_correct"]
        ]
        assert len(wrong_scores) > 0, "No wrong samples in LABELED_SAMPLE"
        mean_wrong = statistics.mean(wrong_scores)
        assert mean_wrong < 0.50, (
            f"Mean score of wrong extractions ({mean_wrong:.4f}) >= 0.50; "
            f"individual scores: {[round(s, 4) for s in wrong_scores]}"
        )


# ===================================================================
# UNIT TESTS — ConfidenceEngine signals in isolation
# ===================================================================

class TestSignalAOCRConfidence:
    """Signal A — OCR word-level confidence (weight 0.40)."""

    def test_empty_confidences_returns_zero(self):
        assert ConfidenceEngine._signal_a_ocr([]) == 0.0

    def test_single_high_confidence(self):
        assert ConfidenceEngine._signal_a_ocr([0.95]) == pytest.approx(0.95)

    def test_mean_of_multiple(self):
        result = ConfidenceEngine._signal_a_ocr([0.80, 0.90, 1.00])
        assert result == pytest.approx(0.90)

    def test_clamps_out_of_range_values(self):
        result = ConfidenceEngine._signal_a_ocr([1.5, -0.2, 0.5])
        # clamped: [1.0, 0.0, 0.5] → mean = 0.5
        assert result == pytest.approx(0.5)


class TestSignalBFormatValidation:
    """Signal B — Field format validation (weight 0.30)."""

    def test_none_value_returns_zero(self):
        assert ConfidenceEngine._signal_b_format("patient_identifier", None) == 0.0

    def test_empty_string_returns_zero(self):
        assert ConfidenceEngine._signal_b_format("patient_identifier", "   ") == 0.0

    def test_valid_date_format(self):
        assert ConfidenceEngine._signal_b_format("document_date", "15/07/2026") == 1.0

    def test_invalid_date_format(self):
        assert ConfidenceEngine._signal_b_format("document_date", "not-a-date") == 0.3

    def test_valid_vitals_format(self):
        assert ConfidenceEngine._signal_b_format("vitals", "120 mmHg") == 1.0

    def test_invalid_vitals_format(self):
        assert ConfidenceEngine._signal_b_format("vitals", "abc xyz") == 0.3

    def test_valid_patient_id(self):
        assert ConfidenceEngine._signal_b_format("patient_identifier", "MRN-123") == 1.0

    def test_diagnosis_too_short(self):
        assert ConfidenceEngine._signal_b_format("diagnosis", "X") == 0.3

    def test_diagnosis_long_enough(self):
        assert ConfidenceEngine._signal_b_format("diagnosis", "Essential Hypertension") == 1.0

    def test_unknown_field_nonempty(self):
        assert ConfidenceEngine._signal_b_format("unknown_field", "some value") == 0.5


class TestSignalCLayoutRegion:
    """Signal C — Layout region bonus (weight 0.20)."""

    def test_correct_region_patient_id(self):
        assert ConfidenceEngine._signal_c_layout("patient_identifier", "header") == 1.0

    def test_wrong_region_patient_id(self):
        assert ConfidenceEngine._signal_c_layout("patient_identifier", "body") == 0.5

    def test_correct_region_vitals(self):
        assert ConfidenceEngine._signal_c_layout("vitals", "table") == 1.0

    def test_correct_region_diagnosis(self):
        assert ConfidenceEngine._signal_c_layout("diagnosis", "body") == 1.0

    def test_unknown_field_neutral(self):
        assert ConfidenceEngine._signal_c_layout("unknown_field", "header") == 0.5


class TestSignalDCrossField:
    """Signal D — Cross-field consistency (weight 0.10)."""

    def test_both_present(self):
        field_map = {"patient_identifier": "P001", "ordering_physician": "Dr. X"}
        assert ConfidenceEngine._signal_d_cross_field(field_map) == 1.0

    def test_one_missing(self):
        field_map = {"patient_identifier": "P001", "ordering_physician": None}
        assert ConfidenceEngine._signal_d_cross_field(field_map) == 0.0

    def test_both_missing(self):
        field_map = {"patient_identifier": None, "ordering_physician": None}
        assert ConfidenceEngine._signal_d_cross_field(field_map) == 0.0

    def test_none_field_map(self):
        assert ConfidenceEngine._signal_d_cross_field(None) == 0.0


class TestConfidenceEngineStateless:
    """Verify the engine is stateless and has no DB dependency."""

    def test_engine_instantiation_no_args(self):
        engine = ConfidenceEngine()
        assert engine is not None

    def test_multiple_calls_independent(self):
        engine = ConfidenceEngine()
        score1 = engine.score_field("patient_identifier", "P001", [0.95])
        score2 = engine.score_field("patient_identifier", None, [])
        # First call should not affect second
        assert score1 != score2
        assert score1 > score2

    def test_score_always_clamped(self):
        engine = ConfidenceEngine()
        # All signals maxed out
        score = engine.score_field(
            "patient_identifier",
            "MRN-123456",
            [1.0, 1.0, 1.0],
            layout_region="header",
            field_map={"patient_identifier": "X", "ordering_physician": "Y"},
        )
        assert 0.0 <= score <= 1.0

        # All signals zeroed
        score_zero = engine.score_field(
            "patient_identifier",
            None,
            [],
            layout_region="body",
            field_map=None,
        )
        assert 0.0 <= score_zero <= 1.0


# ===================================================================
# COMPOSITE SCORE TEST
# ===================================================================

class TestCompositeScoring:
    """End-to-end composite score calculations."""

    def test_perfect_field_scores_high(self):
        """A field with high OCR, matching format, correct region, complete doc."""
        engine = ConfidenceEngine()
        score = engine.score_field(
            field_name="patient_identifier",
            raw_value="MRN-123456",
            ocr_word_confidences=[0.98, 0.97],
            layout_region="header",
            document_type="lab_report",
            field_map={"patient_identifier": "MRN-123456", "ordering_physician": "Dr. X"},
        )
        assert score > 0.85

    def test_null_field_scores_low(self):
        """A missing field with no OCR, wrong region, incomplete doc."""
        engine = ConfidenceEngine()
        score = engine.score_field(
            field_name="patient_identifier",
            raw_value=None,
            ocr_word_confidences=[],
            layout_region="body",
            document_type="unknown",
            field_map={"patient_identifier": None, "ordering_physician": None},
        )
        assert score < 0.15


# ===================================================================
# INTEGRATION TEST — AC-2: Score persisted, not transient
# ===================================================================

SAMPLE_PRESCRIPTION_TEXT = """
CITY GENERAL HOSPITAL - OUTPATIENT CLINIC
Patient Name: Jane Doe
DOB: 1985-04-12
Gender: Female
MRN: MRN-987654
Date: 2026-07-15
Prescribing Doctor: Dr. Robert Adams, MD
Department: Internal Medicine

Diagnosis:
- Essential Hypertension (I10)
- Type 2 Diabetes Mellitus (E11.9)

Rx / Medications:
1. Lisinopril 10mg once daily PO for 30 days
2. Metformin 500mg twice daily PO with meals for 90 days

Instructions:
Take medications as prescribed. Monitor blood pressure weekly.
Signature: Dr. Robert Adams
"""


class TestScorePersistedNotTransient:
    """AC-2: confidence_score is stored in the DB at extraction time."""

    def test_score_persisted_via_api(self, client_as, monkeypatch, tmp_path):
        client = client_as("nurse", patient_access=["*"])
        """POST extract → GET fields → every field_record has a valid confidence_score."""
        dummy_file = tmp_path / "sample_doc.txt"
        dummy_file.write_text(SAMPLE_PRESCRIPTION_TEXT)

        doc_id = str(uuid.uuid4())
        db = TestingSessionLocal()
        try:
            doc = Document(
                document_id=doc_id,
                filename="prescription.pdf",
                raw_uri=str(dummy_file),
                filetype="application/pdf",
                status=DocumentStatus.CLASSIFIED.value,
                document_type="Prescription",
                classification_confidence=0.95,
            )
            db.add(doc)
            db.commit()

            monkeypatch.setattr(
                "app.services.field_extraction_service.extract_text",
                lambda uri, ft: SAMPLE_PRESCRIPTION_TEXT,
            )
            monkeypatch.setattr(
                "app.services.field_extraction_service.get_field_extractor",
                lambda: RuleBasedFieldExtractor(),
            )

            # Trigger extraction
            response = client.post(f"/api/v1/documents/{doc_id}/extract")
            assert response.status_code == 200

            # Retrieve fields
            response = client.get(f"/api/v1/documents/{doc_id}/fields")
            assert response.status_code == 200
            data = response.json()

            assert "field_records" in data
            assert len(data["field_records"]) > 0

            for field_record in data["field_records"]:
                assert "confidence_score" in field_record, (
                    f"confidence_score missing from field_record: {field_record['field_name']}"
                )
                score = field_record["confidence_score"]
                assert isinstance(score, float), (
                    f"confidence_score is not float: {type(score)}"
                )
                assert 0.0 <= score <= 1.0, (
                    f"confidence_score {score} out of range for {field_record['field_name']}"
                )

            # Verify scores are persisted in DB directly (not computed on read)
            db_records = (
                db.query(ExtractedField)
                .filter(ExtractedField.document_id == doc_id)
                .all()
            )
            for rec in db_records:
                assert rec.confidence_score is not None
                assert 0.0 <= rec.confidence_score <= 1.0
        finally:
            db.close()

    def test_confidence_filter_params(self, client, monkeypatch, tmp_path):
        """GET /fields?min_confidence=X&max_confidence=Y filters correctly."""
        dummy_file = tmp_path / "sample_doc.txt"
        dummy_file.write_text(SAMPLE_PRESCRIPTION_TEXT)

        doc_id = str(uuid.uuid4())
        db = TestingSessionLocal()
        try:
            doc = Document(
                document_id=doc_id,
                filename="prescription.pdf",
                raw_uri=str(dummy_file),
                filetype="application/pdf",
                status=DocumentStatus.CLASSIFIED.value,
                document_type="Prescription",
                classification_confidence=0.95,
            )
            db.add(doc)
            db.commit()

            monkeypatch.setattr(
                "app.services.field_extraction_service.extract_text",
                lambda uri, ft: SAMPLE_PRESCRIPTION_TEXT,
            )
            monkeypatch.setattr(
                "app.services.field_extraction_service.get_field_extractor",
                lambda: RuleBasedFieldExtractor(),
            )

            # Trigger extraction first
            client.post(f"/api/v1/documents/{doc_id}/extract")

            # Fetch only high-confidence fields
            response = client.get(
                f"/api/v1/documents/{doc_id}/fields?min_confidence=0.5"
            )
            assert response.status_code == 200
            data = response.json()
            for rec in data["field_records"]:
                assert rec["confidence_score"] >= 0.5

            # Fetch only low-confidence fields
            response = client.get(
                f"/api/v1/documents/{doc_id}/fields?max_confidence=0.3"
            )
            assert response.status_code == 200
            data = response.json()
            for rec in data["field_records"]:
                assert rec["confidence_score"] <= 0.3
        finally:
            db.close()
