"""Tests for the expert node of the decision assistant graph."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from decision.nodes.expert import (
    EXPERT_SYSTEM_PROMPT,
    fan_out_experts,
    run_expert,
)
from decision.schemas import ExpertTask


# ---------------------------------------------------------------------------
# System prompt tests
# ---------------------------------------------------------------------------


class TestExpertSystemPrompt:
    """Validate that the system prompt enforces commitment and structure."""

    def test_contains_role_placeholder(self):
        assert "{role}" in EXPERT_SYSTEM_PROMPT

    def test_contains_options_placeholder(self):
        assert "{options}" in EXPERT_SYSTEM_PROMPT

    def test_contains_constraints_placeholder(self):
        assert "{constraints}" in EXPERT_SYSTEM_PROMPT

    def test_contains_deliverable_placeholder(self):
        assert "{deliverable}" in EXPERT_SYSTEM_PROMPT

    def test_enforces_commitment(self):
        """Prompt must contain language requiring specific commitments."""
        lower = EXPERT_SYSTEM_PROMPT.lower()
        has_commit = "commit" in lower
        has_specific = "specific" in lower
        assert has_commit or has_specific, (
            "Prompt must contain 'commit' or 'specific' to enforce commitment"
        )

    def test_forbids_hedging(self):
        """Prompt must contain language discouraging hedging / 'it depends'."""
        lower = EXPERT_SYSTEM_PROMPT.lower()
        has_hedge = "hedge" in lower
        has_it_depends = "it depends" in lower
        assert has_hedge or has_it_depends, (
            "Prompt must contain 'hedge' or 'it depends' to discourage hedging"
        )

    def test_mentions_score_range(self):
        assert "0-10" in EXPERT_SYSTEM_PROMPT or "0 to 10" in EXPERT_SYSTEM_PROMPT

    def test_mentions_json_output(self):
        assert "JSON" in EXPERT_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# fan_out_experts tests
# ---------------------------------------------------------------------------


class TestFanOutExperts:
    """Verify fan_out_experts produces the right Send objects."""

    def test_returns_correct_count(self):
        state = {
            "expert_tasks": [
                {"expert_role": "analyst", "deliverable": "cost comparison"},
                {"expert_role": "engineer", "deliverable": "tech feasibility"},
                {"expert_role": "legal", "deliverable": "compliance check"},
            ],
            "decision_options": ["Option A", "Option B"],
            "constraints": {"budget": 10000},
        }
        sends = fan_out_experts(state)
        assert len(sends) == 3

    def test_all_sends_target_run_expert(self):
        state = {
            "expert_tasks": [
                {"expert_role": "analyst", "deliverable": "cost comparison"},
                {"expert_role": "engineer", "deliverable": "tech feasibility"},
            ],
            "decision_options": ["A", "B"],
            "constraints": {},
        }
        sends = fan_out_experts(state)
        for send in sends:
            assert send.node == "run_expert"

    def test_send_payloads_contain_task_data(self):
        state = {
            "expert_tasks": [
                {"expert_role": "analyst", "deliverable": "cost comparison"},
            ],
            "decision_options": ["X", "Y"],
            "constraints": {"timeline": "Q2"},
        }
        sends = fan_out_experts(state)
        assert len(sends) == 1
        payload = sends[0].arg
        assert payload["expert_task"]["expert_role"] == "analyst"
        assert payload["decision_options"] == ["X", "Y"]
        assert payload["constraints"] == {"timeline": "Q2"}

    def test_handles_expert_task_model_instances(self):
        """fan_out_experts should handle ExpertTask model instances too."""
        state = {
            "expert_tasks": [
                ExpertTask(expert_role="researcher", deliverable="literature review"),
            ],
            "decision_options": ["A"],
            "constraints": {},
        }
        sends = fan_out_experts(state)
        assert len(sends) == 1
        payload = sends[0].arg
        assert payload["expert_task"]["expert_role"] == "researcher"

    def test_empty_tasks_returns_empty_list(self):
        state = {"expert_tasks": [], "decision_options": ["A"], "constraints": {}}
        sends = fan_out_experts(state)
        assert sends == []

    def test_missing_keys_defaults_gracefully(self):
        state = {}
        sends = fan_out_experts(state)
        assert sends == []


# ---------------------------------------------------------------------------
# run_expert tests (LLM mocked)
# ---------------------------------------------------------------------------


FAKE_EXPERT_OUTPUT: dict[str, Any] = {
    "expert_role": "financial_analyst",
    "option_analyses": {
        "Option A": {
            "option": "Option A",
            "claims": ["Low upfront cost", "High long-term value"],
            "numbers": {"annual_cost": 50000, "roi_percent": 15},
            "risks": ["Market volatility"],
            "score": 8.0,
        },
        "Option B": {
            "option": "Option B",
            "claims": ["Premium support", "Established vendor"],
            "numbers": {"annual_cost": 80000, "roi_percent": 10},
            "risks": ["Vendor lock-in"],
            "score": 6.5,
        },
    },
    "assumptions": ["Stable market conditions", "No regulatory changes"],
    "sources": ["Industry Report 2024", "Vendor pricing sheet"],
    "confidence": 0.85,
}


def _make_mock_llm() -> MagicMock:
    """Return a mock LLM with bind_tools and ainvoke."""
    mock_response = MagicMock()
    mock_response.content = json.dumps(FAKE_EXPERT_OUTPUT)
    mock_response.tool_calls = []

    mock_llm = MagicMock()
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    return mock_llm


class TestRunExpert:
    """Test run_expert with a mocked LLM."""

    @pytest.mark.asyncio
    @patch("decision.nodes.expert._get_expert_llm")
    async def test_returns_expert_outputs_key(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm()

        state = {
            "expert_task": {
                "expert_role": "financial_analyst",
                "deliverable": "cost comparison",
            },
            "decision_options": ["Option A", "Option B"],
            "constraints": {"budget": 100000},
        }
        result = await run_expert(state)

        assert "expert_outputs" in result
        assert "financial_analyst" in result["expert_outputs"]

    @pytest.mark.asyncio
    @patch("decision.nodes.expert._get_expert_llm")
    async def test_output_contains_correct_role(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm()

        state = {
            "expert_task": {
                "expert_role": "financial_analyst",
                "deliverable": "cost comparison",
            },
            "decision_options": ["Option A", "Option B"],
            "constraints": {},
        }
        result = await run_expert(state)

        output = result["expert_outputs"]["financial_analyst"]
        assert output["expert_role"] == "financial_analyst"

    @pytest.mark.asyncio
    @patch("decision.nodes.expert._get_expert_llm")
    async def test_output_has_option_analyses(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm()

        state = {
            "expert_task": {
                "expert_role": "financial_analyst",
                "deliverable": "cost comparison",
            },
            "decision_options": ["Option A", "Option B"],
            "constraints": {},
        }
        result = await run_expert(state)

        output = result["expert_outputs"]["financial_analyst"]
        assert "Option A" in output["option_analyses"]
        assert "Option B" in output["option_analyses"]

    @pytest.mark.asyncio
    @patch("decision.nodes.expert._get_expert_llm")
    async def test_output_has_confidence(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm()

        state = {
            "expert_task": {
                "expert_role": "financial_analyst",
                "deliverable": "cost comparison",
            },
            "decision_options": ["Option A", "Option B"],
            "constraints": {},
        }
        result = await run_expert(state)

        output = result["expert_outputs"]["financial_analyst"]
        assert output["confidence"] == 0.85

    @pytest.mark.asyncio
    @patch("decision.nodes.expert._get_expert_llm")
    async def test_parse_error_returns_minimal_output(self, mock_get_llm: MagicMock):
        """When the LLM returns invalid JSON, we get a minimal output."""
        mock_response = MagicMock()
        mock_response.content = "This is not valid JSON at all"
        mock_response.tool_calls = []

        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        mock_get_llm.return_value = mock_llm

        state = {
            "expert_task": {
                "expert_role": "analyst",
                "deliverable": "analysis",
            },
            "decision_options": ["Option A"],
            "constraints": {},
        }
        result = await run_expert(state)

        assert "expert_outputs" in result
        output = result["expert_outputs"]["analyst"]
        assert output["confidence"] == 0.0
        assert output["expert_role"] == "analyst"

    @pytest.mark.asyncio
    @patch("decision.nodes.expert._get_expert_llm")
    async def test_handles_expert_task_as_dict(self, mock_get_llm: MagicMock):
        """run_expert should handle expert_task as a plain dict."""
        mock_get_llm.return_value = _make_mock_llm()

        state = {
            "expert_task": {
                "expert_role": "financial_analyst",
                "deliverable": "cost comparison",
            },
            "decision_options": ["Option A", "Option B"],
            "constraints": {},
        }
        result = await run_expert(state)
        assert "financial_analyst" in result["expert_outputs"]

    @pytest.mark.asyncio
    @patch("decision.nodes.expert._get_expert_llm")
    async def test_bind_tools_called(self, mock_get_llm: MagicMock):
        """The LLM must have bind_tools called with search and calculator."""
        mock_llm = _make_mock_llm()
        mock_get_llm.return_value = mock_llm

        state = {
            "expert_task": {
                "expert_role": "financial_analyst",
                "deliverable": "cost comparison",
            },
            "decision_options": ["Option A"],
            "constraints": {},
        }
        await run_expert(state)

        mock_llm.bind_tools.assert_called_once()
        tools_arg = mock_llm.bind_tools.call_args[0][0]
        assert len(tools_arg) == 2

    @pytest.mark.asyncio
    @patch("decision.nodes.expert._get_expert_llm")
    async def test_tool_calling_loop(self, mock_get_llm: MagicMock):
        """When the LLM returns tool calls, the loop should execute them."""
        # First response: tool call
        tool_call_response = MagicMock()
        tool_call_response.content = ""
        tool_call_response.tool_calls = [
            {
                "name": "calculator",
                "args": {"expression": "2 + 2"},
                "id": "call_123",
            }
        ]

        # Second response: final answer (no tool calls)
        final_response = MagicMock()
        final_response.content = json.dumps(FAKE_EXPERT_OUTPUT)
        final_response.tool_calls = []

        mock_llm = MagicMock()
        mock_llm.bind_tools = MagicMock(return_value=mock_llm)
        mock_llm.ainvoke = AsyncMock(side_effect=[tool_call_response, final_response])
        mock_get_llm.return_value = mock_llm

        state = {
            "expert_task": {
                "expert_role": "financial_analyst",
                "deliverable": "cost comparison",
            },
            "decision_options": ["Option A", "Option B"],
            "constraints": {},
        }
        result = await run_expert(state)

        # Should have called ainvoke twice (tool call round + final)
        assert mock_llm.ainvoke.call_count == 2
        assert "financial_analyst" in result["expert_outputs"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
