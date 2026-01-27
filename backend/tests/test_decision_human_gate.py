"""Tests for the human gate node and routing logic."""

from __future__ import annotations

import pytest

from decision.nodes.human_gate import route_after_human


# ---------------------------------------------------------------------------
# route_after_human tests (pure function -- no async needed)
# ---------------------------------------------------------------------------


class TestRouteAfterHuman:
    """Test the routing function that follows the human gate."""

    def test_returns_synthesizer_when_action_is_proceed(self):
        state = {
            "human_feedback": {"action": "proceed"},
            "iteration": 1,
            "max_iterations": 3,
        }
        assert route_after_human(state) == "synthesizer"

    def test_returns_fan_out_experts_when_re_analyze_under_max(self):
        state = {
            "human_feedback": {"action": "re_analyze"},
            "iteration": 1,
            "max_iterations": 3,
        }
        assert route_after_human(state) == "fan_out_experts"

    def test_returns_synthesizer_when_re_analyze_at_max(self):
        state = {
            "human_feedback": {"action": "re_analyze"},
            "iteration": 3,
            "max_iterations": 3,
        }
        assert route_after_human(state) == "synthesizer"

    def test_returns_synthesizer_when_re_analyze_above_max(self):
        state = {
            "human_feedback": {"action": "re_analyze"},
            "iteration": 5,
            "max_iterations": 3,
        }
        assert route_after_human(state) == "synthesizer"

    def test_returns_synthesizer_when_feedback_is_none(self):
        state = {
            "human_feedback": None,
            "iteration": 0,
            "max_iterations": 3,
        }
        assert route_after_human(state) == "synthesizer"

    def test_returns_synthesizer_when_feedback_key_missing(self):
        state = {
            "iteration": 0,
            "max_iterations": 3,
        }
        assert route_after_human(state) == "synthesizer"

    def test_returns_synthesizer_for_unknown_action(self):
        state = {
            "human_feedback": {"action": "unknown_action"},
            "iteration": 1,
            "max_iterations": 3,
        }
        assert route_after_human(state) == "synthesizer"

    def test_returns_fan_out_when_iteration_is_zero(self):
        state = {
            "human_feedback": {"action": "re_analyze"},
            "iteration": 0,
            "max_iterations": 3,
        }
        assert route_after_human(state) == "fan_out_experts"

    def test_returns_synthesizer_when_re_analyze_at_max_boundary(self):
        """Edge case: iteration == max_iterations - should go to synthesizer."""
        state = {
            "human_feedback": {"action": "re_analyze"},
            "iteration": 2,
            "max_iterations": 2,
        }
        assert route_after_human(state) == "synthesizer"

    def test_defaults_max_iterations_to_3(self):
        """When max_iterations is not in state, default is 3."""
        state = {
            "human_feedback": {"action": "re_analyze"},
            "iteration": 1,
        }
        assert route_after_human(state) == "fan_out_experts"

    def test_defaults_iteration_to_0(self):
        """When iteration is not in state, default is 0."""
        state = {
            "human_feedback": {"action": "re_analyze"},
            "max_iterations": 3,
        }
        assert route_after_human(state) == "fan_out_experts"

    def test_empty_feedback_dict_defaults_to_proceed(self):
        """Empty dict with no 'action' key should default to proceed."""
        state = {
            "human_feedback": {},
            "iteration": 1,
            "max_iterations": 3,
        }
        assert route_after_human(state) == "synthesizer"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
