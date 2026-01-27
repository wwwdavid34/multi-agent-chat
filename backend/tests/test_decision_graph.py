"""Tests for the decision assistant graph assembly."""

from __future__ import annotations

import pytest

from decision.graph import _route_after_conflicts, build_decision_graph


# ---------------------------------------------------------------------------
# Graph compilation tests
# ---------------------------------------------------------------------------


class TestBuildDecisionGraph:
    """Verify that build_decision_graph() produces a valid compiled graph."""

    def test_graph_compiles(self):
        graph = build_decision_graph()
        assert graph is not None

    def test_graph_has_expected_nodes(self):
        graph = build_decision_graph()
        node_names = set(graph.nodes.keys())
        expected = {"planner", "run_expert", "conflict_detector", "human_gate", "synthesizer"}
        assert expected.issubset(node_names), (
            f"Missing nodes: {expected - node_names}"
        )


# ---------------------------------------------------------------------------
# Routing function tests
# ---------------------------------------------------------------------------


class TestRouteAfterConflicts:
    """Verify _route_after_conflicts routing logic."""

    def test_route_after_conflicts_with_conflicts(self):
        state = {
            "conflicts": [
                {
                    "conflict_type": "numeric",
                    "topic": "cost estimate",
                    "experts": ["analyst", "engineer"],
                    "values": ["50000", "72000"],
                }
            ]
        }
        result = _route_after_conflicts(state)
        assert result == "human_gate"

    def test_route_after_conflicts_no_conflicts(self):
        state = {"conflicts": []}
        result = _route_after_conflicts(state)
        assert result == "synthesizer"

    def test_route_after_conflicts_missing_key(self):
        """When 'conflicts' is absent from state, default to synthesizer."""
        state = {}
        result = _route_after_conflicts(state)
        assert result == "synthesizer"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
