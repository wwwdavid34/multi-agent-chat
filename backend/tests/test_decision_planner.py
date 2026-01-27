"""Tests for the planner node of the decision assistant graph."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from decision.nodes.planner import PLANNER_SYSTEM_PROMPT, planner_node


# ---------------------------------------------------------------------------
# System prompt tests
# ---------------------------------------------------------------------------


class TestPlannerSystemPrompt:
    """Validate that the system prompt contains essential instructions."""

    def test_contains_decision_options_keyword(self):
        assert "decision_options" in PLANNER_SYSTEM_PROMPT

    def test_contains_expert_tasks_keyword(self):
        assert "expert_tasks" in PLANNER_SYSTEM_PROMPT

    def test_contains_json_keyword(self):
        assert "JSON" in PLANNER_SYSTEM_PROMPT

    def test_contains_expert_role_keyword(self):
        assert "expert_role" in PLANNER_SYSTEM_PROMPT

    def test_contains_deliverable_keyword(self):
        assert "deliverable" in PLANNER_SYSTEM_PROMPT

    def test_mentions_option_count_range(self):
        assert "2" in PLANNER_SYSTEM_PROMPT and "5" in PLANNER_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# planner_node integration tests (LLM mocked)
# ---------------------------------------------------------------------------


FAKE_LLM_RESPONSE: dict[str, Any] = {
    "decision_options": ["Option A", "Option B", "Option C"],
    "expert_tasks": [
        {"expert_role": "financial_analyst", "deliverable": "cost comparison table"},
        {"expert_role": "engineer", "deliverable": "technical feasibility report"},
    ],
}


def _make_mock_llm() -> MagicMock:
    """Return a mock LLM whose ``ainvoke`` returns a realistic response."""
    mock_response = MagicMock()
    mock_response.content = json.dumps(FAKE_LLM_RESPONSE)

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    return mock_llm


class TestPlannerNode:
    """Test planner_node with a mocked LLM."""

    @pytest.mark.asyncio
    @patch("decision.nodes.planner._get_planner_llm")
    async def test_returns_expected_keys(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm()

        state = {
            "user_question": "Which cloud provider should we use?",
            "constraints": {"budget": 10000},
        }
        result = await planner_node(state)

        assert "decision_options" in result
        assert "expert_tasks" in result
        assert "phase" in result

    @pytest.mark.asyncio
    @patch("decision.nodes.planner._get_planner_llm")
    async def test_phase_is_analysis(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm()

        state = {"user_question": "Pick a database"}
        result = await planner_node(state)

        assert result["phase"] == "analysis"

    @pytest.mark.asyncio
    @patch("decision.nodes.planner._get_planner_llm")
    async def test_decision_options_match_llm_response(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm()

        state = {"user_question": "Which vendor?"}
        result = await planner_node(state)

        assert result["decision_options"] == FAKE_LLM_RESPONSE["decision_options"]

    @pytest.mark.asyncio
    @patch("decision.nodes.planner._get_planner_llm")
    async def test_expert_tasks_match_llm_response(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm()

        state = {"user_question": "Which vendor?"}
        result = await planner_node(state)

        assert result["expert_tasks"] == FAKE_LLM_RESPONSE["expert_tasks"]

    @pytest.mark.asyncio
    @patch("decision.nodes.planner._get_planner_llm")
    async def test_llm_receives_constraints_in_message(self, mock_get_llm: MagicMock):
        mock_llm = _make_mock_llm()
        mock_get_llm.return_value = mock_llm

        constraints = {"budget": 5000, "timeline": "Q2"}
        state = {
            "user_question": "Which tool?",
            "constraints": constraints,
        }
        await planner_node(state)

        # Inspect messages passed to ainvoke
        call_args = mock_llm.ainvoke.call_args
        messages = call_args[0][0]
        human_msg_content = messages[1].content

        assert "budget" in human_msg_content
        assert "5000" in human_msg_content
        assert "Q2" in human_msg_content

    @pytest.mark.asyncio
    @patch("decision.nodes.planner._get_planner_llm")
    async def test_works_without_constraints(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm()

        state = {"user_question": "Best option?"}
        result = await planner_node(state)

        # Should still succeed and return all expected keys
        assert "decision_options" in result
        assert "expert_tasks" in result
        assert result["phase"] == "analysis"

    @pytest.mark.asyncio
    @patch("decision.nodes.planner._get_planner_llm")
    async def test_works_with_empty_state(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm()

        state = {}
        result = await planner_node(state)

        assert "decision_options" in result
        assert "expert_tasks" in result
        assert result["phase"] == "analysis"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
