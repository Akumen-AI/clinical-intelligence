"""
Unit tests for the handwriting routing decision logic.

Tests app.services.handwriting.routing.should_route_to_handwriting()
which decides whether PaddleOCR output should be re-processed through
a multimodal vision model based on per-fragment confidence scores.
"""

import pytest

from app.services.handwriting.routing import should_route_to_handwriting


class TestShouldRouteToHandwriting:
    """Tests for the confidence-based routing decision."""

    # --- Default thresholds used across most tests ---
    CONF_THRESHOLD = 0.65
    PROP_THRESHOLD = 0.40

    def test_all_high_confidence_does_not_route(self):
        """Printed text with all scores above threshold → no routing."""
        scores = [0.95, 0.92, 0.98, 0.91, 0.97]
        assert should_route_to_handwriting(scores, self.CONF_THRESHOLD, self.PROP_THRESHOLD) is False

    def test_all_low_confidence_routes(self):
        """All fragments below threshold → definitely route."""
        scores = [0.30, 0.25, 0.40, 0.15, 0.50]
        assert should_route_to_handwriting(scores, self.CONF_THRESHOLD, self.PROP_THRESHOLD) is True

    def test_empty_scores_does_not_route(self):
        """No OCR fragments at all → nothing to improve on, don't route."""
        assert should_route_to_handwriting([], self.CONF_THRESHOLD, self.PROP_THRESHOLD) is False

    def test_proportion_exactly_at_boundary_does_not_route(self):
        """Proportion == threshold (not strictly above) → don't route.

        With 10 fragments, 4 below threshold = 0.40 proportion.
        The function requires proportion > threshold (strict), so this
        should NOT route.
        """
        # Interleave so there is no consecutive cluster of 3
        scores = [0.30, 0.70, 0.40, 0.80, 0.50, 0.90, 0.60, 0.95, 0.92, 0.88]  # 4 below 0.65, max consecutive is 1
        proportion = 4 / 10  # exactly 0.40
        assert proportion == self.PROP_THRESHOLD
        assert should_route_to_handwriting(scores, self.CONF_THRESHOLD, self.PROP_THRESHOLD) is False

    def test_proportion_just_above_boundary_routes(self):
        """Proportion just above threshold → route.

        With 10 fragments, 5 below threshold = 0.50 proportion > 0.40.
        """
        scores = [0.30, 0.40, 0.50, 0.60, 0.55,  # 5 below 0.65
                  0.70, 0.80, 0.90, 0.95, 0.92]    # 5 above
        assert should_route_to_handwriting(scores, self.CONF_THRESHOLD, self.PROP_THRESHOLD) is True

    def test_mixed_scores_below_proportion_does_not_route(self):
        """Some low scores but not enough proportion → don't route.

        Simulates a mostly-printed document with minor noise.
        """
        # 2 out of 10 below threshold = 0.20 < 0.40
        scores = [0.45, 0.55,  # 2 below 0.65
                  0.70, 0.80, 0.90, 0.95, 0.92, 0.88, 0.75, 0.85]  # 8 above
        assert should_route_to_handwriting(scores, self.CONF_THRESHOLD, self.PROP_THRESHOLD) is False

    def test_single_fragment_below_threshold_does_not_route(self):
        """A single low-confidence fragment among many high ones → don't route."""
        scores = [0.30] + [0.95] * 9  # 1/10 = 0.10 < 0.40
        assert should_route_to_handwriting(scores, self.CONF_THRESHOLD, self.PROP_THRESHOLD) is False

    def test_single_fragment_below_threshold_with_low_proportion_threshold(self):
        """With a very low proportion threshold, even one bad fragment triggers routing."""
        scores = [0.30, 0.95, 0.90]  # 1/3 = 0.33
        # proportion_threshold = 0.30 → 0.33 > 0.30 → route
        assert should_route_to_handwriting(scores, self.CONF_THRESHOLD, 0.30) is True

    def test_custom_thresholds(self):
        """Verify that custom threshold values are respected."""
        scores = [0.75, 0.78, 0.80, 0.72, 0.85]
        # With confidence_threshold=0.80: 4/5 = 0.80 below threshold
        # With proportion_threshold=0.50: 0.80 > 0.50 → route
        assert should_route_to_handwriting(scores, 0.80, 0.50) is True
        # With proportion_threshold=0.90: 0.80 < 0.90 → don't route
        assert should_route_to_handwriting(scores, 0.80, 0.90) is False

    def test_scores_exactly_at_confidence_threshold_are_not_low(self):
        """Fragments scoring exactly at the threshold are NOT counted as low."""
        # All at 0.65 exactly → 0 below threshold → don't route
        scores = [0.65, 0.65, 0.65, 0.65, 0.65]
        assert should_route_to_handwriting(scores, self.CONF_THRESHOLD, self.PROP_THRESHOLD) is False

    def test_single_element_below_threshold(self):
        """Single-element list below threshold → proportion=1.0 > any reasonable threshold."""
        scores = [0.30]
        assert should_route_to_handwriting(scores, self.CONF_THRESHOLD, self.PROP_THRESHOLD) is True

    def test_single_element_above_threshold(self):
        """Single-element list above threshold → proportion=0.0."""
        scores = [0.90]
        assert should_route_to_handwriting(scores, self.CONF_THRESHOLD, self.PROP_THRESHOLD) is False

    def test_consecutive_cluster_triggers_routing_despite_low_proportion(self):
        """A cluster of consecutive low-confidence scores (e.g. 3 Rx lines in a 20-line doc) routes."""
        # 3 low scores out of 20 = 15% proportion (which is <= 0.40 PROP_THRESHOLD)
        scores = [0.95] * 10 + [0.40, 0.35, 0.45] + [0.95] * 7
        assert should_route_to_handwriting(scores, self.CONF_THRESHOLD, self.PROP_THRESHOLD, consecutive_count_threshold=3) is True

    def test_isolated_low_scores_do_not_trigger_cluster_routing(self):
        """Scattered low scores below cluster threshold and below proportion threshold do not route."""
        # 2 isolated low scores scattered in 20 lines
        scores = [0.95] * 5 + [0.40] + [0.95] * 8 + [0.35] + [0.95] * 5
        assert should_route_to_handwriting(scores, self.CONF_THRESHOLD, self.PROP_THRESHOLD, consecutive_count_threshold=3) is False

    def test_cluster_threshold_disabled_when_none(self):
        """When consecutive_count_threshold is None, only proportion threshold is used."""
        scores = [0.95] * 10 + [0.40, 0.35, 0.45] + [0.95] * 7  # 3/20 = 0.15 <= 0.40
        assert should_route_to_handwriting(scores, self.CONF_THRESHOLD, self.PROP_THRESHOLD, consecutive_count_threshold=None) is False

