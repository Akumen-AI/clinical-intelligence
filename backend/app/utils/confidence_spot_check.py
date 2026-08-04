import json
import math
import os
from typing import Any, Dict, List
from app.services.confidence_service import aggregate_field_confidence, get_field_status


def run_spot_check(labeled_sample_path: str) -> Dict[str, Any]:
    """
    Run spot-check validation on labeled synthetic/real OCR field samples.

    Args:
        labeled_sample_path: Path to JSON file containing labeled samples.

    Returns:
        dict: {"pass_rate": float, "field_results": [...]}
    """
    abs_path = os.path.abspath(labeled_sample_path)
    if not os.path.exists(abs_path):
        raise FileNotFoundError(f"Labeled sample file not found at: {abs_path}")

    with open(abs_path, "r", encoding="utf-8") as f:
        samples = json.load(f)

    field_results = []
    scores: List[float] = []
    passed_count = 0

    for sample in samples:
        field_name = sample.get("field_name", "unknown")
        raw_value = sample.get("raw_value")
        expected_range = sample.get("expected_confidence_range", [0.0, 1.0])
        bbox = sample.get("bounding_box")

        # Determine OCR input data for confidence aggregation
        if "paddle_result" in sample:
            ocr_data = sample["paddle_result"]
        elif "char_confidences" in sample:
            ocr_data = sample["char_confidences"]
        else:
            ocr_data = None

        calc_confidence = aggregate_field_confidence(ocr_data, bbox)
        scores.append(calc_confidence)

        status_flag = get_field_status(calc_confidence, raw_value)

        # Check if score falls within expected confidence range [min_val, max_val]
        min_expected, max_expected = expected_range[0], expected_range[1]
        passed = (min_expected <= round(calc_confidence, 4) <= max_expected) or (
            calc_confidence >= min_expected and calc_confidence <= max_expected
        )

        if passed:
            passed_count += 1

        field_results.append({
            "field_name": field_name,
            "raw_value": raw_value,
            "calculated_confidence": round(calc_confidence, 4),
            "expected_range": expected_range,
            "status": status_flag,
            "passed": passed
        })

    total_samples = len(samples)
    pass_rate = passed_count / total_samples if total_samples > 0 else 0.0

    # Calculate distribution statistics: min, max, mean, std
    if scores:
        min_score = min(scores)
        max_score = max(scores)
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        std_score = math.sqrt(variance)
    else:
        min_score = max_score = mean_score = std_score = 0.0

    print("==================================================")
    print("      CONFIDENCE SCORING SPOT-CHECK SUMMARY       ")
    print("==================================================")
    print(f"Total Samples Evaluated : {total_samples}")
    print(f"Passed Range Check      : {passed_count} / {total_samples}")
    print(f"Pass Rate               : {pass_rate * 100:.2f}%")
    print("--------------------------------------------------")
    print("SCORE DISTRIBUTION SUMMARY:")
    print(f"  Min  Score : {min_score:.4f}")
    print(f"  Max  Score : {max_score:.4f}")
    print(f"  Mean Score : {mean_score:.4f}")
    print(f"  Std  Dev   : {std_score:.4f}")
    print("==================================================")

    return {
        "pass_rate": round(pass_rate, 4),
        "field_results": field_results,
        "distribution_summary": {
            "min": round(min_score, 4),
            "max": round(max_score, 4),
            "mean": round(mean_score, 4),
            "std": round(std_score, 4)
        }
    }


if __name__ == "__main__":
    import sys
    fixture_file = sys.argv[1] if len(sys.argv) > 1 else "tests/fixtures/confidence_labels.json"
    run_spot_check(fixture_file)
