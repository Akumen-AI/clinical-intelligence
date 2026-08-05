"""
Confidence Scoring Engine — Story 2.3 (FR-08)

Stateless, unit-testable engine that computes a composite confidence score
for every extracted clinical field.  The score combines four weighted signals:

  Signal A (0.40) — OCR word-level confidence (mean of per-word probabilities)
  Signal B (0.30) — Field format validation (regex / rule per field type)
  Signal C (0.20) — Layout region bonus (expected vs. actual region)
  Signal D (0.10) — Cross-field consistency (document completeness heuristic)

The engine has NO database dependency — it operates purely on the inputs
passed to ``score_field()`` and is safe to instantiate in tests without
any fixtures or mocks.
"""

import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Signal B — per-field format validation patterns
# ---------------------------------------------------------------------------
_FORMAT_RULES: Dict[str, re.Pattern] = {
    "patient_identifier": re.compile(r"\S+"),          # any non-empty value
    "document_date":      re.compile(r"\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}"),
    "vitals":             re.compile(r"\d+(\.\d+)?\s*(mmHg|bpm|°[CF]|kg|lbs|cm|%|/min)"),
    "medications":        re.compile(r"\S+"),           # non-empty after strip
    "diagnosis":          re.compile(r".{4,}"),         # non-empty, len > 3
    "ordering_physician": re.compile(r"\S+"),           # non-empty
    "lab_results":        re.compile(r"\S+"),           # non-empty
    "symptoms":           re.compile(r"\S+"),           # non-empty
    "procedures":         re.compile(r"\S+"),           # non-empty
}

# ---------------------------------------------------------------------------
# Signal C — expected layout region per field
# ---------------------------------------------------------------------------
_EXPECTED_REGIONS: Dict[str, str] = {
    "patient_identifier":  "header",
    "document_date":       "header",
    "diagnosis":           "body",
    "medications":         "body",
    "vitals":              "table",
    "ordering_physician":  "header",
    "lab_results":         "table",
    "symptoms":            "body",
    "procedures":          "body",
}


class ConfidenceEngine:
    """Stateless scorer — instantiate freely, no side effects."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def score_field(
        self,
        field_name: str,
        raw_value: Optional[str],
        ocr_word_confidences: Optional[List[float]] = None,
        layout_region: str = "body",
        document_type: str = "unknown",
        field_map: Optional[Dict[str, Optional[str]]] = None,
        document_id: Optional[str] = None,
    ) -> float:
        """Compute a composite confidence score in [0.0, 1.0].

        Parameters
        ----------
        field_name:
            Clinical field key, e.g. ``"patient_identifier"``.
        raw_value:
            The stringified extraction value (``None`` when absent).
            For complex values (dicts/lists from JSON fields), the caller
            should pass a non-None sentinel string such as ``"<present>"``
            when the value is logically present.
        ocr_word_confidences:
            Per-word OCR probabilities for this field, already in [0, 1].
        layout_region:
            The layout region where this field was detected
            (``"header"`` | ``"body"`` | ``"table"`` | ``"other"``).
        document_type:
            The classified document type, e.g. ``"lab_report"``.
        field_map:
            Full field→value mapping for the same document (enables Signal D).
        document_id:
            Optional document ID — used only for the structured log line.

        Returns
        -------
        float
            Confidence score rounded to 4 decimal places, clamped to [0, 1].
        """
        if ocr_word_confidences is None:
            ocr_word_confidences = []

        signal_a = self._signal_a_ocr(ocr_word_confidences)
        signal_b = self._signal_b_format(field_name, raw_value)
        signal_c = self._signal_c_layout(field_name, layout_region)
        signal_d = self._signal_d_cross_field(field_map)

        raw_score = (
            0.40 * signal_a
            + 0.30 * signal_b
            + 0.20 * signal_c
            + 0.10 * signal_d
        )
        score = round(min(max(raw_score, 0.0), 1.0), 4)

        logger.info(
            "confidence_scored",
            extra={
                "document_id": document_id,
                "field_name": field_name,
                "score": score,
                "signal_a": round(signal_a, 4),
                "signal_b": round(signal_b, 4),
                "signal_c": round(signal_c, 4),
                "signal_d": round(signal_d, 4),
            },
        )

        return score

    # ------------------------------------------------------------------
    # Signal implementations
    # ------------------------------------------------------------------
    @staticmethod
    def _signal_a_ocr(ocr_word_confidences: List[float]) -> float:
        """Signal A — OCR word-level confidence (weight 0.40).

        Returns the arithmetic mean of per-word probabilities.
        If the list is empty, returns 0.0.
        """
        if not ocr_word_confidences:
            return 0.0
        # Clamp individual values to [0, 1] defensively
        clamped = [min(max(float(c), 0.0), 1.0) for c in ocr_word_confidences]
        return sum(clamped) / len(clamped)

    @staticmethod
    def _signal_b_format(field_name: str, raw_value: Optional[str]) -> float:
        """Signal B — Field format validation (weight 0.30).

        Returns 1.0 if the value matches the expected format, 0.3 if it does
        not match, or 0.0 if the value is None/empty.
        """
        if raw_value is None:
            return 0.0
        value_str = str(raw_value).strip()
        if not value_str:
            return 0.0
        pattern = _FORMAT_RULES.get(field_name)
        if pattern is None:
            # Unknown field — give partial credit if non-empty
            return 0.5
        return 1.0 if pattern.search(value_str) else 0.3

    @staticmethod
    def _signal_c_layout(field_name: str, layout_region: str) -> float:
        """Signal C — Layout region bonus (weight 0.20).

        Returns 1.0 if the field appears in its expected region, else 0.5.
        """
        expected = _EXPECTED_REGIONS.get(field_name)
        if expected is None:
            return 0.5  # Unknown field — neutral
        return 1.0 if layout_region == expected else 0.5

    @staticmethod
    def _signal_d_cross_field(field_map: Optional[Dict[str, Optional[str]]]) -> float:
        """Signal D — Cross-field consistency (weight 0.10).

        Returns 1.0 if both ``ordering_physician`` and ``patient_identifier``
        are non-null in the document's field map, rewarding "complete" documents.
        Otherwise returns 0.0.
        """
        if field_map is None:
            return 0.0
        has_physician = field_map.get("ordering_physician") is not None
        has_patient = field_map.get("patient_identifier") is not None
        return 1.0 if (has_physician and has_patient) else 0.0
