"""
Unit tests for the evaluation harness's accuracy calculation logic.

Tests the comparison and scoring functions used by
scripts/evaluate_handwriting_extraction.py to measure extraction accuracy
against ground truth.

Per the user's feedback:
- Safety-critical fields (drug names, dosage, numeric values) use EXACT match
- Free-text fields (patient name, doctor name, notes) use FUZZY match (≥0.85)
- Both metrics are reported; the split-by-field-type approach avoids hiding
  clinically dangerous near-misses under a blanket fuzzy-match KPI.
"""

import pytest
from difflib import SequenceMatcher


# ---------------------------------------------------------------------------
# These functions mirror the logic that will live in
# scripts/evaluate_handwriting_extraction.py — tested here in isolation.
# ---------------------------------------------------------------------------

# Fields where exact match is required (after normalization) because even
# small differences are clinically significant (e.g., "50mg" vs "500mg").
EXACT_MATCH_FIELDS = {
    "medication_name", "dosage", "frequency", "route", "duration",
    "test_name", "value", "unit", "reference_range",
    "patient_id", "dob",
}

# Fields where fuzzy match (≥0.85 char similarity) is acceptable because
# minor formatting/spelling variations are not clinically dangerous.
FUZZY_MATCH_FIELDS = {
    "name", "gender", "department", "npi_or_license",
    "condition_name", "icd10_code", "notes", "instructions",
    "document_date", "symptoms", "procedures",
}

FUZZY_THRESHOLD = 0.85


def normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, strip, collapse whitespace."""
    if not text:
        return ""
    import re
    return re.sub(r"\s+", " ", text.strip().lower())


def is_exact_match(expected: str, actual: str) -> bool:
    """Case-insensitive, whitespace-normalized exact match."""
    return normalize(expected) == normalize(actual)


def is_fuzzy_match(expected: str, actual: str, threshold: float = FUZZY_THRESHOLD) -> bool:
    """Fuzzy match using SequenceMatcher ratio ≥ threshold."""
    if not expected and not actual:
        return True
    if not expected or not actual:
        return False
    ratio = SequenceMatcher(None, normalize(expected), normalize(actual)).ratio()
    return ratio >= threshold


def field_matches(field_name: str, expected: str, actual: str) -> dict:
    """
    Compute match results for a single field.

    Returns a dict with:
      - exact_match: bool
      - fuzzy_match: bool
      - field_type: "exact" or "fuzzy" (which metric governs this field)
      - pass: bool (whether the field passes its governing metric)
    """
    exact = is_exact_match(expected, actual)
    fuzzy = is_fuzzy_match(expected, actual)

    # Determine which metric governs this field
    if field_name in EXACT_MATCH_FIELDS:
        field_type = "exact"
        passed = exact
    elif field_name in FUZZY_MATCH_FIELDS:
        field_type = "fuzzy"
        passed = fuzzy
    else:
        # Unknown field — default to exact match for safety
        field_type = "exact"
        passed = exact

    return {
        "exact_match": exact,
        "fuzzy_match": fuzzy,
        "field_type": field_type,
        "pass": passed,
    }


def compute_accuracy(results: list) -> dict:
    """
    Compute overall and field-type-specific accuracy from a list of
    field_matches results.

    Returns:
      - overall_accuracy: float (blended across all fields)
      - exact_field_accuracy: float (only fields governed by exact match)
      - fuzzy_field_accuracy: float (only fields governed by fuzzy match)
      - total_fields: int
      - passed_fields: int
    """
    if not results:
        return {
            "overall_accuracy": 0.0,
            "exact_field_accuracy": 0.0,
            "fuzzy_field_accuracy": 0.0,
            "total_fields": 0,
            "passed_fields": 0,
        }

    total = len(results)
    passed = sum(1 for r in results if r["pass"])

    exact_results = [r for r in results if r["field_type"] == "exact"]
    fuzzy_results = [r for r in results if r["field_type"] == "fuzzy"]

    exact_acc = (
        sum(1 for r in exact_results if r["pass"]) / len(exact_results)
        if exact_results else 0.0
    )
    fuzzy_acc = (
        sum(1 for r in fuzzy_results if r["pass"]) / len(fuzzy_results)
        if fuzzy_results else 0.0
    )

    return {
        "overall_accuracy": passed / total,
        "exact_field_accuracy": exact_acc,
        "fuzzy_field_accuracy": fuzzy_acc,
        "total_fields": total,
        "passed_fields": passed,
    }


# ===========================================================================
# Tests
# ===========================================================================

class TestNormalization:
    def test_basic_normalization(self):
        assert normalize("  Hello   World  ") == "hello world"

    def test_case_insensitive(self):
        assert normalize("AMOXICILLIN") == "amoxicillin"

    def test_empty_string(self):
        assert normalize("") == ""

    def test_none_returns_empty(self):
        assert normalize(None) == ""

    def test_tabs_and_newlines_collapsed(self):
        assert normalize("hello\t\tworld\n") == "hello world"


class TestExactMatch:
    def test_identical_strings(self):
        assert is_exact_match("500mg", "500mg") is True

    def test_case_difference(self):
        assert is_exact_match("Amoxicillin", "amoxicillin") is True

    def test_whitespace_difference(self):
        assert is_exact_match("500 mg", "500  mg") is True

    def test_different_values(self):
        assert is_exact_match("500mg", "50mg") is False

    def test_similar_drug_names(self):
        """Prednisone vs Prednisolone — different drugs, must NOT match."""
        assert is_exact_match("Prednisone", "Prednisolone") is False

    def test_empty_strings(self):
        assert is_exact_match("", "") is True


class TestFuzzyMatch:
    def test_identical_strings(self):
        assert is_fuzzy_match("John Smith", "John Smith") is True

    def test_minor_difference(self):
        """Small variation in a long name should pass fuzzy."""
        assert is_fuzzy_match("Dr. Jonathan Smith", "Dr. Jonathon Smith") is True

    def test_threshold_boundary_pass(self):
        """Two strings with exactly 0.85+ similarity."""
        # "abcdefghijklmnop" (16 chars) vs "abcdefghijklmnox" (1 diff)
        # Ratio should be ~0.9375
        assert is_fuzzy_match("abcdefghijklmnop", "abcdefghijklmnox") is True

    def test_threshold_boundary_fail(self):
        """Two strings with similarity below 0.85."""
        assert is_fuzzy_match("hello", "world") is False

    def test_empty_both(self):
        assert is_fuzzy_match("", "") is True

    def test_empty_one(self):
        assert is_fuzzy_match("hello", "") is False
        assert is_fuzzy_match("", "hello") is False

    def test_dosage_near_miss_fails_exact(self):
        """50mg vs 500mg — fuzzy might pass but exact must not."""
        # This demonstrates WHY safety-critical fields need exact match
        assert is_exact_match("50mg", "500mg") is False
        # Fuzzy might pass since they share characters
        ratio = SequenceMatcher(None, normalize("50mg"), normalize("500mg")).ratio()
        # Just verify the exact-match catches it regardless of fuzzy outcome
        assert is_exact_match("50mg", "500mg") is False


class TestFieldMatches:
    def test_exact_field_exact_match(self):
        """Dosage field with perfect match passes."""
        result = field_matches("dosage", "500mg", "500mg")
        assert result["pass"] is True
        assert result["field_type"] == "exact"

    def test_exact_field_mismatch(self):
        """Dosage field with wrong value fails."""
        result = field_matches("dosage", "500mg", "50mg")
        assert result["pass"] is False
        assert result["field_type"] == "exact"

    def test_fuzzy_field_close_match(self):
        """Name field with minor typo passes fuzzy."""
        result = field_matches("name", "Dr. Jonathan Smith", "Dr. Jonathon Smith")
        assert result["pass"] is True
        assert result["field_type"] == "fuzzy"

    def test_fuzzy_field_major_mismatch(self):
        """Name field with completely different value fails even fuzzy."""
        result = field_matches("name", "Dr. Smith", "Dr. Williams")
        assert result["pass"] is False
        assert result["field_type"] == "fuzzy"

    def test_unknown_field_defaults_to_exact(self):
        """Unknown field names default to exact match for safety."""
        result = field_matches("unknown_field", "hello", "hello")
        assert result["pass"] is True
        assert result["field_type"] == "exact"

    def test_drug_name_exact_match_required(self):
        """Drug names (medication_name) require exact match."""
        result = field_matches("medication_name", "Prednisone", "Prednisolone")
        assert result["pass"] is False
        assert result["field_type"] == "exact"


class TestComputeAccuracy:
    def test_perfect_accuracy(self):
        results = [
            {"exact_match": True, "fuzzy_match": True, "field_type": "exact", "pass": True},
            {"exact_match": True, "fuzzy_match": True, "field_type": "fuzzy", "pass": True},
            {"exact_match": True, "fuzzy_match": True, "field_type": "exact", "pass": True},
        ]
        acc = compute_accuracy(results)
        assert acc["overall_accuracy"] == 1.0
        assert acc["exact_field_accuracy"] == 1.0
        assert acc["fuzzy_field_accuracy"] == 1.0
        assert acc["total_fields"] == 3
        assert acc["passed_fields"] == 3

    def test_zero_accuracy(self):
        results = [
            {"exact_match": False, "fuzzy_match": False, "field_type": "exact", "pass": False},
            {"exact_match": False, "fuzzy_match": False, "field_type": "fuzzy", "pass": False},
        ]
        acc = compute_accuracy(results)
        assert acc["overall_accuracy"] == 0.0
        assert acc["exact_field_accuracy"] == 0.0
        assert acc["fuzzy_field_accuracy"] == 0.0

    def test_mixed_accuracy(self):
        results = [
            {"exact_match": True, "fuzzy_match": True, "field_type": "exact", "pass": True},
            {"exact_match": False, "fuzzy_match": True, "field_type": "fuzzy", "pass": True},
            {"exact_match": False, "fuzzy_match": False, "field_type": "exact", "pass": False},
            {"exact_match": False, "fuzzy_match": False, "field_type": "fuzzy", "pass": False},
        ]
        acc = compute_accuracy(results)
        assert acc["overall_accuracy"] == 0.5  # 2 of 4
        assert acc["exact_field_accuracy"] == 0.5  # 1 of 2 exact fields
        assert acc["fuzzy_field_accuracy"] == 0.5  # 1 of 2 fuzzy fields

    def test_empty_results(self):
        acc = compute_accuracy([])
        assert acc["overall_accuracy"] == 0.0
        assert acc["total_fields"] == 0

    def test_kpi_check_against_threshold(self):
        """Verify the 90% KPI target check works correctly."""
        # 9 of 10 pass
        results = [
            {"exact_match": True, "fuzzy_match": True, "field_type": "exact", "pass": True}
            for _ in range(9)
        ] + [
            {"exact_match": False, "fuzzy_match": False, "field_type": "exact", "pass": False}
        ]
        acc = compute_accuracy(results)
        assert acc["overall_accuracy"] == 0.9
        assert acc["overall_accuracy"] >= 0.90  # KPI target met

    def test_kpi_check_below_threshold(self):
        """Verify the 90% KPI check correctly identifies failure."""
        # 8 of 10 pass
        results = [
            {"exact_match": True, "fuzzy_match": True, "field_type": "exact", "pass": True}
            for _ in range(8)
        ] + [
            {"exact_match": False, "fuzzy_match": False, "field_type": "exact", "pass": False}
            for _ in range(2)
        ]
        acc = compute_accuracy(results)
        assert acc["overall_accuracy"] == 0.8
        assert acc["overall_accuracy"] < 0.90  # KPI target NOT met
