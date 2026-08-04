import os
from typing import Any, List, Optional, Union


def _parse_bbox(bbox: Any) -> Optional[tuple[float, float, float, float]]:
    """Helper to convert bounding_box to (xmin, ymin, xmax, ymax) tuple."""
    if not bbox:
        return None
    if isinstance(bbox, dict):
        return (
            float(bbox.get("xmin", bbox.get("x1", 0))),
            float(bbox.get("ymin", bbox.get("y1", 0))),
            float(bbox.get("xmax", bbox.get("x2", 0))),
            float(bbox.get("ymax", bbox.get("y2", 0)))
        )
    if isinstance(bbox, (list, tuple)) and len(bbox) >= 4:
        # Check if polygon format [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
        if isinstance(bbox[0], (list, tuple)):
            xs = [pt[0] for pt in bbox]
            ys = [pt[1] for pt in bbox]
            return (min(xs), min(ys), max(xs), max(ys))
        return (float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3]))
    return None


def _bbox_overlaps(
    box1: tuple[float, float, float, float],
    box2: tuple[float, float, float, float]
) -> bool:
    """Check if two bounding boxes overlap."""
    b1_x1, b1_y1, b1_x2, b1_y2 = box1
    b2_x1, b2_y1, b2_x2, b2_y2 = box2
    return not (b1_x2 < b2_x1 or b1_x1 > b2_x2 or b1_y2 < b2_y1 or b1_y1 > b2_y2)


def aggregate_field_confidence(paddle_result: Any, bounding_box: Any = None) -> float:
    """
    Extract character-level confidence scores within the bounding box region
    and calculate their arithmetic MEAN.

    Args:
        paddle_result: PaddleOCR output structure or custom list/dict of results.
            Can be:
            - Standard PaddleOCR list: result[page_idx][line_idx] where
              line is [poly, (text, char_confidences_or_score)]
            - Direct list of lines: result[line_idx] = [poly, (text, char_confidences)]
            - Dict or object with char_confidences or rec_scores
            - List of floats directly representing char confidences
        bounding_box: Bounding box region [xmin, ymin, xmax, ymax], polygon, or dict.

    Returns:
        float: Aggregated mean confidence in range [0.0, 1.0]. Returns 0.0 if no characters detected.
    """
    if not paddle_result:
        return 0.0

    target_bbox = _parse_bbox(bounding_box)
    char_confidences: List[float] = []

    # Case 0: paddle_result is a list of numeric floats directly
    if isinstance(paddle_result, (list, tuple)) and all(isinstance(x, (int, float)) for x in paddle_result):
        char_confidences = [float(x) for x in paddle_result]
    elif isinstance(paddle_result, dict):
        # Dict with char_confidences or rec_scores
        if "char_confidences" in paddle_result:
            char_confidences = [float(c) for c in paddle_result["char_confidences"]]
        elif "rec_scores" in paddle_result:
            char_confidences = [float(c) for c in paddle_result["rec_scores"]]
    else:
        # Standard PaddleOCR result list structure
        # Flatten page level if outer list contains page results
        lines = paddle_result
        if isinstance(lines, (list, tuple)) and len(lines) > 0:
            if isinstance(lines[0], (list, tuple)) and len(lines[0]) > 0 and isinstance(lines[0][0], (list, tuple)) and len(lines[0][0]) == 2 and isinstance(lines[0][0][0], (list, tuple)):
                # Nested page list: paddle_result[0] is list of lines
                lines = lines[0]

        for line in lines:
            if not isinstance(line, (list, tuple)) or len(line) < 2:
                continue

            poly_or_box = line[0]
            text_info = line[1]

            # Bounding box filter check if target_bbox provided
            if target_bbox and poly_or_box:
                line_bbox = _parse_bbox(poly_or_box)
                if line_bbox and not _bbox_overlaps(target_bbox, line_bbox):
                    continue

            # Extract confidences from text_info
            if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                text_str = text_info[0]
                conf_data = text_info[1]

                if isinstance(conf_data, (list, tuple)):
                    # List of character confidences: result[line_idx][1][1]
                    char_confidences.extend(float(c) for c in conf_data)
                elif isinstance(conf_data, (int, float)):
                    # Single line confidence score: assign to each character in text_str
                    if text_str:
                        char_confidences.extend([float(conf_data)] * len(text_str))
                    else:
                        char_confidences.append(float(conf_data))

    if not char_confidences:
        return 0.0

    mean_conf = sum(char_confidences) / len(char_confidences)
    # Clamp to [0.0, 1.0] range
    return max(0.0, min(1.0, float(mean_conf)))


def get_field_status(confidence: float, raw_value: Optional[str] = None) -> str:
    """
    Determine extraction field status based on confidence score and raw value.

    Args:
        confidence: Confidence score in range [0.0, 1.0].
        raw_value: Extracted string value.

    Returns:
        str: Status enum value ('auto_approved', 'pending_review', 'illegible', or 'human_verified').
    """
    threshold = float(os.getenv("CONFIDENCE_THRESHOLD", "0.75"))

    if raw_value is None or not str(raw_value).strip() or confidence <= 0.0:
        return "illegible"
    if confidence >= threshold:
        return "auto_approved"
    return "pending_review"
