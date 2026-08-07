"""
Pure-function routing logic for deciding when to invoke the handwriting
extraction path instead of accepting PaddleOCR output.

The current v1 heuristic operates at the page level: if a high enough
proportion of OCR text fragments score below a confidence threshold,
we infer the page likely contains handwritten or illegible content.

# TODO (v2): Field-region-level confidence routing
# Prescriptions are often mixed — printed letterhead/clinic info with
# handwritten drug name and dosage.  A whole-page proportion metric gets
# diluted by the printed boilerplate and can fail to trigger even when the
# clinically important part (the handwritten bit) is illegible.
#
# Once layout regions from app/models/layout_region.py are available per
# fragment, a more precise v2 heuristic would compute confidence within
# each layout region independently and route only the regions that need it.
# This avoids the dilution problem and also lets us send a tighter crop
# to the vision model, improving accuracy and reducing token cost.
"""

from typing import List, Optional


def should_route_to_handwriting(
    ocr_scores: List[float],
    confidence_threshold: float,
    proportion_threshold: float,
    consecutive_count_threshold: Optional[int] = 3,
) -> bool:
    """
    Decide whether OCR output suggests handwritten / illegible content.

    Args:
        ocr_scores: Per-fragment recognition confidence scores from PaddleOCR
            (each in [0.0, 1.0]).  An empty list means no text was detected
            at all — we do NOT route in that case (nothing for the vision
            model to improve on).
        confidence_threshold: Fragments scoring below this are counted as
            "low confidence" (e.g. 0.65).
        proportion_threshold: The fraction of low-confidence fragments
            required to trigger handwriting routing (e.g. 0.15 means >15%).
        consecutive_count_threshold: Optional number of consecutive low-confidence
            fragments required to trigger routing regardless of overall page proportion.
            If None or <= 0, cluster routing is skipped.

    Returns:
        True if the proportion of low-confidence fragments strictly exceeds
        proportion_threshold OR a consecutive cluster of low-confidence fragments
        meets consecutive_count_threshold; False otherwise.
    """
    if not ocr_scores:
        return False

    low_count = sum(1 for s in ocr_scores if s < confidence_threshold)
    proportion = low_count / len(ocr_scores)

    if proportion > proportion_threshold:
        return True

    # Check for consecutive low-confidence cluster (e.g. handwritten Rx amidst printed letterhead)
    if consecutive_count_threshold and consecutive_count_threshold > 0:
        current_run = 0
        for s in ocr_scores:
            if s < confidence_threshold:
                current_run += 1
                if current_run >= consecutive_count_threshold:
                    return True
            else:
                current_run = 0

    return False
