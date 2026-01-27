"""Tests for decision assistant schemas and state model."""

from __future__ import annotations

import pytest

from decision.schemas import (
    Conflict,
    ExpertOutput,
    ExpertTask,
    HumanFeedback,
    OptionAnalysis,
    Recommendation,
)
from decision.state import DecisionState, merge_expert_outputs


# ---------------------------------------------------------------------------
# Schema creation tests
# ---------------------------------------------------------------------------


class TestExpertTask:
    """Test ExpertTask schema."""

    def test_create(self):
        task = ExpertTask(expert_role="financial_analyst", deliverable="cost comparison")
        assert task.expert_role == "financial_analyst"
        assert task.deliverable == "cost comparison"


class TestOptionAnalysis:
    """Test OptionAnalysis schema."""

    def test_create_minimal(self):
        analysis = OptionAnalysis(option="Option A", claims=["claim1"], score=7.5)
        assert analysis.option == "Option A"
        assert analysis.claims == ["claim1"]
        assert analysis.numbers == {}
        assert analysis.risks == []
        assert analysis.score == 7.5

    def test_create_full(self):
        analysis = OptionAnalysis(
            option="Option B",
            claims=["c1", "c2"],
            numbers={"cost": 1000, "time_weeks": 4},
            risks=["vendor lock-in"],
            score=6.0,
        )
        assert analysis.numbers["cost"] == 1000
        assert len(analysis.risks) == 1

    def test_score_bounds_lower(self):
        with pytest.raises(Exception):
            OptionAnalysis(option="X", claims=["c"], score=-1)

    def test_score_bounds_upper(self):
        with pytest.raises(Exception):
            OptionAnalysis(option="X", claims=["c"], score=11)


class TestExpertOutput:
    """Test ExpertOutput schema."""

    def test_create(self):
        analysis = OptionAnalysis(option="A", claims=["claim"], score=5.0)
        output = ExpertOutput(
            expert_role="engineer",
            option_analyses={"A": analysis},
            confidence=0.8,
        )
        assert output.expert_role == "engineer"
        assert "A" in output.option_analyses
        assert output.assumptions == []
        assert output.sources == []
        assert output.confidence == 0.8

    def test_confidence_bounds_lower(self):
        analysis = OptionAnalysis(option="A", claims=["c"], score=5.0)
        with pytest.raises(Exception):
            ExpertOutput(
                expert_role="eng",
                option_analyses={"A": analysis},
                confidence=-0.1,
            )

    def test_confidence_bounds_upper(self):
        analysis = OptionAnalysis(option="A", claims=["c"], score=5.0)
        with pytest.raises(Exception):
            ExpertOutput(
                expert_role="eng",
                option_analyses={"A": analysis},
                confidence=1.1,
            )


class TestConflict:
    """Test Conflict schema."""

    def test_create(self):
        conflict = Conflict(
            conflict_type="data",
            topic="cost estimate",
            experts=["engineer", "analyst"],
            values=["$1000", "$5000"],
        )
        assert conflict.conflict_type == "data"
        assert conflict.topic == "cost estimate"
        assert len(conflict.experts) == 2
        assert len(conflict.values) == 2


class TestHumanFeedback:
    """Test HumanFeedback schema."""

    def test_create_minimal(self):
        fb = HumanFeedback(action="approve")
        assert fb.action == "approve"
        assert fb.approved_assumptions == []
        assert fb.rejected_assumptions == []
        assert fb.removed_options == []
        assert fb.updated_constraints == {}
        assert fb.additional_instructions == ""

    def test_create_full(self):
        fb = HumanFeedback(
            action="revise",
            approved_assumptions=["a1"],
            rejected_assumptions=["a2"],
            removed_options=["Option C"],
            updated_constraints={"budget": 5000},
            additional_instructions="Focus on long-term ROI",
        )
        assert fb.action == "revise"
        assert fb.approved_assumptions == ["a1"]
        assert fb.rejected_assumptions == ["a2"]
        assert fb.removed_options == ["Option C"]
        assert fb.updated_constraints["budget"] == 5000
        assert "ROI" in fb.additional_instructions


class TestRecommendation:
    """Test Recommendation schema."""

    def test_create(self):
        rec = Recommendation(
            recommended_option="Option A",
            reasoning=["lowest cost", "fastest delivery"],
            tradeoffs={
                "Option A": {"pro": "cheap", "con": "less features"},
                "Option B": {"pro": "full-featured", "con": "expensive"},
            },
            risks=["vendor may raise prices"],
            what_would_change_mind=["budget doubles", "timeline extends"],
            confidence=0.75,
        )
        assert rec.recommended_option == "Option A"
        assert len(rec.reasoning) == 2
        assert len(rec.tradeoffs) == 2
        assert len(rec.risks) == 1
        assert len(rec.what_would_change_mind) == 2
        assert rec.confidence == 0.75

    def test_confidence_bounds_lower(self):
        with pytest.raises(Exception):
            Recommendation(
                recommended_option="X",
                reasoning=["r"],
                tradeoffs={},
                risks=[],
                what_would_change_mind=[],
                confidence=-0.1,
            )

    def test_confidence_bounds_upper(self):
        with pytest.raises(Exception):
            Recommendation(
                recommended_option="X",
                reasoning=["r"],
                tradeoffs={},
                risks=[],
                what_would_change_mind=[],
                confidence=1.1,
            )


# ---------------------------------------------------------------------------
# State / reducer tests
# ---------------------------------------------------------------------------


class TestMergeExpertOutputs:
    """Test the merge_expert_outputs reducer function."""

    def test_merge_both_none(self):
        result = merge_expert_outputs(None, None)
        assert result == {}

    def test_merge_existing_none(self):
        analysis = OptionAnalysis(option="A", claims=["c"], score=5.0)
        new = {
            "engineer": ExpertOutput(
                expert_role="engineer",
                option_analyses={"A": analysis},
                confidence=0.9,
            )
        }
        result = merge_expert_outputs(None, new)
        assert "engineer" in result

    def test_merge_new_none(self):
        analysis = OptionAnalysis(option="A", claims=["c"], score=5.0)
        existing = {
            "analyst": ExpertOutput(
                expert_role="analyst",
                option_analyses={"A": analysis},
                confidence=0.7,
            )
        }
        result = merge_expert_outputs(existing, None)
        assert "analyst" in result

    def test_merge_both_non_empty(self):
        analysis = OptionAnalysis(option="A", claims=["c"], score=5.0)
        existing = {
            "analyst": ExpertOutput(
                expert_role="analyst",
                option_analyses={"A": analysis},
                confidence=0.7,
            )
        }
        new = {
            "engineer": ExpertOutput(
                expert_role="engineer",
                option_analyses={"A": analysis},
                confidence=0.9,
            )
        }
        result = merge_expert_outputs(existing, new)
        assert "analyst" in result
        assert "engineer" in result
        assert len(result) == 2

    def test_merge_overwrites_existing_key(self):
        analysis_v1 = OptionAnalysis(option="A", claims=["old"], score=3.0)
        analysis_v2 = OptionAnalysis(option="A", claims=["new"], score=8.0)
        existing = {
            "analyst": ExpertOutput(
                expert_role="analyst",
                option_analyses={"A": analysis_v1},
                confidence=0.5,
            )
        }
        new = {
            "analyst": ExpertOutput(
                expert_role="analyst",
                option_analyses={"A": analysis_v2},
                confidence=0.9,
            )
        }
        result = merge_expert_outputs(existing, new)
        assert result["analyst"].confidence == 0.9
        assert result["analyst"].option_analyses["A"].claims == ["new"]


class TestDecisionState:
    """Test that DecisionState can be imported and used."""

    def test_import(self):
        """DecisionState should be importable as a TypedDict."""
        assert DecisionState is not None

    def test_empty_state(self):
        """An empty dict satisfies DecisionState (total=False)."""
        state: DecisionState = {}
        assert isinstance(state, dict)

    def test_partial_state(self):
        """A partially-filled state should work fine."""
        state: DecisionState = {
            "user_question": "Which cloud provider?",
            "phase": "planning",
            "iteration": 0,
            "max_iterations": 3,
        }
        assert state["user_question"] == "Which cloud provider?"
        assert state["phase"] == "planning"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
