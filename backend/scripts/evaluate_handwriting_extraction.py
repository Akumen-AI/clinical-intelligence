#!/usr/bin/env python3
"""
Evaluation harness for handwriting extraction accuracy.

Runs the full extraction pipeline (including handwriting routing) against
every synthetic sample in scripts/handwriting_testset/, compares extracted
field values to ground truth, and computes accuracy metrics.

Scoring approach (per user feedback):
  - EXACT MATCH (after normalization) for safety-critical fields:
    drug names, dosages, frequencies, numeric values
  - FUZZY MATCH (≥0.85 SequenceMatcher ratio) for free-text fields:
    patient names, doctor names, notes, dates
  - Both metrics are reported; the field-type breakdown is the number
    that actually matters for a clinical KPI decision.

Output:
  - Timestamped JSON report to eval_reports/
  - Concise stdout summary

Usage:
    python scripts/evaluate_handwriting_extraction.py

NOTE: This requires GEMINI_API_KEY to be set if any samples trigger
the handwriting routing path. Set it in backend/.env.
"""

import json
import os
import re
import sys
import time
from datetime import datetime
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Tuple

# Add the backend directory to the Python path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TESTSET_DIR = os.path.join(SCRIPT_DIR, "handwriting_testset")
EVAL_REPORTS_DIR = os.path.join(BACKEND_DIR, "eval_reports")
KPI_TARGET = 0.90

# Fields where exact match is required (safety-critical)
EXACT_MATCH_FIELDS = {
    "drug_name", "dosage", "frequency",
    "medication_name", "value", "unit", "reference_range",
    "test_name", "patient_id", "dob",
}

# Fields where fuzzy match is acceptable (free-text)
FUZZY_MATCH_FIELDS = {
    "patient_name", "doctor_name", "name",
    "gender", "department", "npi_or_license",
    "condition_name", "icd10_code", "notes", "instructions",
    "document_date", "symptoms", "procedures",
}

FUZZY_THRESHOLD = 0.85


# ---------------------------------------------------------------------------
# Comparison functions
# ---------------------------------------------------------------------------

def normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, strip, collapse whitespace."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip().lower())


def is_exact_match(expected: str, actual: str) -> bool:
    """Case-insensitive, whitespace-normalized exact match."""
    return normalize(expected) == normalize(actual)


def is_fuzzy_match(expected: str, actual: str, threshold: float = FUZZY_THRESHOLD) -> bool:
    """Fuzzy match using SequenceMatcher ratio."""
    if not expected and not actual:
        return True
    if not expected or not actual:
        return False
    ratio = SequenceMatcher(None, normalize(expected), normalize(actual)).ratio()
    return ratio >= threshold


def compute_similarity(expected: str, actual: str) -> float:
    """Compute SequenceMatcher similarity ratio."""
    if not expected and not actual:
        return 1.0
    if not expected or not actual:
        return 0.0
    return SequenceMatcher(None, normalize(expected), normalize(actual)).ratio()


def field_match_result(field_name: str, expected: str, actual: str) -> dict:
    """Compute match results for a single field."""
    exact = is_exact_match(expected, actual)
    fuzzy = is_fuzzy_match(expected, actual)
    similarity = compute_similarity(expected, actual)

    if field_name in EXACT_MATCH_FIELDS:
        field_type = "exact"
        passed = exact
    elif field_name in FUZZY_MATCH_FIELDS:
        field_type = "fuzzy"
        passed = fuzzy
    else:
        field_type = "exact"
        passed = exact

    return {
        "field_name": field_name,
        "expected": expected,
        "actual": actual,
        "exact_match": exact,
        "fuzzy_match": fuzzy,
        "similarity": round(similarity, 4),
        "field_type": field_type,
        "pass": passed,
    }


# ---------------------------------------------------------------------------
# Extraction pipeline
# ---------------------------------------------------------------------------

def extract_fields_from_image(image_path: str) -> Dict[str, str]:
    """
    Run the extraction pipeline on an image and return extracted field values.

    Uses extract_text_with_confidence → routing decision → handwriting or
    standard extraction.
    """
    from app.config import settings
    from app.services.text_extraction_service import extract_text_with_confidence
    from app.services.handwriting.routing import should_route_to_handwriting

    # Get OCR text and confidence scores
    # The filepath needs to be relative to backend dir for extract_text_with_confidence
    rel_path = os.path.relpath(image_path, BACKEND_DIR)
    ext = os.path.splitext(image_path)[1].lstrip(".").lower()

    ocr_text, ocr_scores = extract_text_with_confidence(rel_path, ext)

    extracted_fields = {}
    extraction_method = "paddleocr"

    # Check if we should route to handwriting extraction
    if (
        ocr_scores
        and settings.HANDWRITING_EXTRACTION_ENABLED
        and settings.GEMINI_API_KEY
        and should_route_to_handwriting(
            ocr_scores,
            confidence_threshold=settings.HANDWRITING_OCR_CONFIDENCE_THRESHOLD,
            proportion_threshold=settings.HANDWRITING_LOW_CONFIDENCE_PROPORTION,
        )
    ):
        extraction_method = "gemini_handwriting"
        try:
            from app.services.handwriting.factory import get_handwriting_extractor
            hw_extractor = get_handwriting_extractor()
            result = hw_extractor.extract_from_image(image_path)

            # Map the structured fields to our flat field names
            fields = result.fields
            if fields.patient_identifier and fields.patient_identifier.name:
                extracted_fields["patient_name"] = fields.patient_identifier.name
            if fields.document_date:
                extracted_fields["document_date"] = fields.document_date
            if fields.ordering_physician and fields.ordering_physician.name:
                extracted_fields["doctor_name"] = fields.ordering_physician.name
            if fields.medications:
                med = fields.medications[0]  # First medication
                if med.medication_name:
                    extracted_fields["drug_name"] = med.medication_name
                if med.dosage:
                    extracted_fields["dosage"] = med.dosage
                if med.frequency:
                    extracted_fields["frequency"] = med.frequency

        except Exception as e:
            print(f"  [!] Handwriting extraction failed: {e}")
            extraction_method = "paddleocr_fallback"

    # If we didn't get fields from handwriting extraction, try to extract from OCR text
    if not extracted_fields and ocr_text:
        extraction_method = "paddleocr"
        # Basic text-based field extraction from OCR output
        extracted_fields = _extract_fields_from_text(ocr_text)

    return extracted_fields, extraction_method


def _extract_fields_from_text(text: str) -> dict:
    """
    Simple regex/heuristic extraction from OCR text for evaluation purposes.
    This is intentionally basic — the real pipeline uses LLM-based extraction.
    """
    fields = {}
    lines = text.split("\n")
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        # Try to find field patterns
        lower = line_stripped.lower()
        if "patient" in lower and "name" in lower:
            parts = line_stripped.split(":", 1)
            if len(parts) > 1:
                fields["patient_name"] = parts[1].strip()
        if "date" in lower:
            parts = line_stripped.split(":", 1)
            if len(parts) > 1:
                val = parts[1].strip()
                if val:
                    fields["document_date"] = val
    return fields


# ---------------------------------------------------------------------------
# Main evaluation
# ---------------------------------------------------------------------------

def evaluate():
    """Run the full evaluation harness."""
    os.makedirs(EVAL_REPORTS_DIR, exist_ok=True)

    # Load manifest
    manifest_path = os.path.join(TESTSET_DIR, "manifest.json")
    if not os.path.exists(manifest_path):
        print(f"Error: Test set not found at {TESTSET_DIR}")
        print("Run 'python scripts/generate_handwriting_testset.py' first.")
        sys.exit(1)

    with open(manifest_path) as f:
        manifest = json.load(f)

    print(f"Evaluating {len(manifest)} samples from {TESTSET_DIR}")
    print(f"KPI target: {KPI_TARGET:.0%}")
    print(f"Fuzzy threshold: {FUZZY_THRESHOLD}")
    print("=" * 60)

    # Load settings for report
    try:
        from app.config import settings
        threshold_info = {
            "handwriting_ocr_confidence_threshold": settings.HANDWRITING_OCR_CONFIDENCE_THRESHOLD,
            "handwriting_low_confidence_proportion": settings.HANDWRITING_LOW_CONFIDENCE_PROPORTION,
            "handwriting_extraction_enabled": settings.HANDWRITING_EXTRACTION_ENABLED,
        }
    except Exception:
        threshold_info = {}

    all_results = []
    per_sample_results = []
    per_tier_results = {"clean": [], "moderate": [], "degraded": []}
    method_counts = {}

    start_time = time.time()

    for entry in manifest:
        sample_id = entry["sample_id"]
        tier = entry["tier"]
        img_file = entry["image_file"]
        gt_file = entry["ground_truth_file"]

        img_path = os.path.join(TESTSET_DIR, img_file)
        gt_path = os.path.join(TESTSET_DIR, gt_file)

        # Load ground truth
        with open(gt_path) as f:
            gt = json.load(f)
        gt_fields = gt["fields"]

        print(f"\n[{sample_id:03d}] {tier}/{entry['font']}: ", end="")

        # Extract fields
        try:
            extracted, method = extract_fields_from_image(img_path)
            method_counts[method] = method_counts.get(method, 0) + 1
        except Exception as e:
            print(f"EXTRACTION FAILED: {e}")
            extracted = {}
            method = "error"

        # Compare each ground truth field
        sample_field_results = []
        for field_name, expected_value in gt_fields.items():
            actual_value = extracted.get(field_name, "")
            result = field_match_result(field_name, str(expected_value), str(actual_value))
            sample_field_results.append(result)
            all_results.append(result)
            per_tier_results[tier].append(result)

        # Summary for this sample
        passed = sum(1 for r in sample_field_results if r["pass"])
        total = len(sample_field_results)
        status = "✓" if passed == total else "✗"
        print(f"{status} {passed}/{total} fields ({method})")

        per_sample_results.append({
            "sample_id": sample_id,
            "tier": tier,
            "font": entry["font"],
            "method": method,
            "fields": sample_field_results,
            "passed": passed,
            "total": total,
        })

    elapsed = time.time() - start_time

    # ---------------------------------------------------------------------------
    # Compute aggregate metrics
    # ---------------------------------------------------------------------------

    total_fields = len(all_results)
    total_passed = sum(1 for r in all_results if r["pass"])

    exact_results = [r for r in all_results if r["field_type"] == "exact"]
    fuzzy_results = [r for r in all_results if r["field_type"] == "fuzzy"]

    overall_accuracy = total_passed / total_fields if total_fields else 0
    exact_accuracy = (
        sum(1 for r in exact_results if r["pass"]) / len(exact_results)
        if exact_results else 0
    )
    fuzzy_accuracy = (
        sum(1 for r in fuzzy_results if r["pass"]) / len(fuzzy_results)
        if fuzzy_results else 0
    )

    # Per-field accuracy
    per_field_accuracy = {}
    for field_name in set(r["field_name"] for r in all_results):
        field_results = [r for r in all_results if r["field_name"] == field_name]
        field_passed = sum(1 for r in field_results if r["pass"])
        per_field_accuracy[field_name] = {
            "accuracy": round(field_passed / len(field_results), 4) if field_results else 0,
            "passed": field_passed,
            "total": len(field_results),
            "field_type": field_results[0]["field_type"] if field_results else "unknown",
        }

    # Per-tier accuracy
    per_tier_accuracy = {}
    for tier_name, tier_results in per_tier_results.items():
        if tier_results:
            tier_passed = sum(1 for r in tier_results if r["pass"])
            per_tier_accuracy[tier_name] = {
                "accuracy": round(tier_passed / len(tier_results), 4),
                "passed": tier_passed,
                "total": len(tier_results),
            }

    kpi_met = overall_accuracy >= KPI_TARGET

    # ---------------------------------------------------------------------------
    # Build report
    # ---------------------------------------------------------------------------

    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "kpi_target": KPI_TARGET,
        "kpi_met": kpi_met,
        "overall_accuracy": round(overall_accuracy, 4),
        "exact_field_accuracy": round(exact_accuracy, 4),
        "fuzzy_field_accuracy": round(fuzzy_accuracy, 4),
        "total_fields_evaluated": total_fields,
        "total_fields_passed": total_passed,
        "sample_count": len(manifest),
        "elapsed_seconds": round(elapsed, 2),
        "fuzzy_threshold": FUZZY_THRESHOLD,
        "extraction_methods": method_counts,
        "thresholds": threshold_info,
        "per_field_accuracy": per_field_accuracy,
        "per_tier_accuracy": per_tier_accuracy,
        "per_sample_results": per_sample_results,
    }

    # Save report
    timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_filename = f"handwriting_extraction_eval_{timestamp_str}.json"
    report_path = os.path.join(EVAL_REPORTS_DIR, report_filename)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)

    # ---------------------------------------------------------------------------
    # Print summary
    # ---------------------------------------------------------------------------

    print("\n" + "=" * 60)
    print("EVALUATION SUMMARY")
    print("=" * 60)
    print(f"  Samples:            {len(manifest)}")
    print(f"  Total fields:       {total_fields}")
    print(f"  Fields passed:      {total_passed}")
    print(f"  Overall accuracy:   {overall_accuracy:.1%}")
    print(f"  Exact-match fields: {exact_accuracy:.1%} ({len(exact_results)} fields)")
    print(f"  Fuzzy-match fields: {fuzzy_accuracy:.1%} ({len(fuzzy_results)} fields)")
    print(f"  Elapsed:            {elapsed:.1f}s")
    print()
    print("  Per-tier accuracy:")
    for tier_name in ["clean", "moderate", "degraded"]:
        info = per_tier_accuracy.get(tier_name, {})
        acc = info.get("accuracy", 0)
        print(f"    {tier_name:12s}: {acc:.1%} ({info.get('passed', 0)}/{info.get('total', 0)})")
    print()
    print("  Per-field accuracy:")
    for field_name, info in sorted(per_field_accuracy.items()):
        marker = "[exact]" if info["field_type"] == "exact" else "[fuzzy]"
        print(f"    {field_name:20s} {marker:8s}: {info['accuracy']:.1%} ({info['passed']}/{info['total']})")
    print()
    print("  Extraction methods:")
    for method, count in sorted(method_counts.items()):
        print(f"    {method:25s}: {count}")
    print()

    if kpi_met:
        print(f"  ✅ KPI TARGET MET: {overall_accuracy:.1%} >= {KPI_TARGET:.0%}")
    else:
        print(f"  ❌ KPI TARGET NOT MET: {overall_accuracy:.1%} < {KPI_TARGET:.0%}")
        print(f"     This is a valid and expected outcome to surface for synthetic data.")
        print(f"     Exact-match accuracy on safety-critical fields: {exact_accuracy:.1%}")

    print()
    print(f"  Report saved: {report_path}")
    print("=" * 60)


if __name__ == "__main__":
    evaluate()
