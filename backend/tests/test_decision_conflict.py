"""Tests for the conflict detector node of the decision assistant graph."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from decision.nodes.conflict_detector import (
    DETECTOR_SYSTEM_PROMPT,
    conflict_detector_node,
)


# ---------------------------------------------------------------------------
# System prompt tests
# ---------------------------------------------------------------------------


class TestDetectorSystemPrompt:
    """Validate that the system prompt contains essential detection rules."""

    def test_mentions_numeric_conflict(self):
        lower = DETECTOR_SYSTEM_PROMPT.lower()
        assert "numeric" in lower

    def test_mentions_20_percent_threshold(self):
        assert "20%" in DETECTOR_SYSTEM_PROMPT

    def test_mentions_assumption_mismatch(self):
        lower = DETECTOR_SYSTEM_PROMPT.lower()
        assert "assumption" in lower and "mismatch" in lower

    def test_mentions_risk_disagreement(self):
        lower = DETECTOR_SYSTEM_PROMPT.lower()
        assert "risk" in lower and "disagreement" in lower

    def test_mentions_coverage_gap(self):
        lower = DETECTOR_SYSTEM_PROMPT.lower()
        assert "coverage" in lower and "gap" in lower

    def test_does_not_resolve_conflicts(self):
        lower = DETECTOR_SYSTEM_PROMPT.lower()
        assert "not resolve" in lower or "do not resolve" in lower

    def test_mentions_json_output(self):
        assert "JSON" in DETECTOR_SYSTEM_PROMPT

    def test_output_keys_specified(self):
        assert "conflicts" in DETECTOR_SYSTEM_PROMPT
        assert "open_questions" in DETECTOR_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# conflict_detector_node tests (LLM mocked)
# ---------------------------------------------------------------------------


FAKE_CONFLICTS_RESPONSE: dict[str, Any] = {
    "conflicts": [
        {
            "conflict_type": "numeric",
            "topic": "annual_cost for Option A",
            "experts": ["financial_analyst", "engineer"],
            "values": ["50000", "72000"],
        },
        {
            "conflict_type": "assumption_mismatch",
            "topic": "market stability assumption",
            "experts": ["financial_analyst", "market_researcher"],
            "values": [
                "Stable market conditions",
                "Volatile market expected",
            ],
        },
    ],
    "open_questions": [
        "What is the expected timeline for regulatory changes?",
        "Does the budget include training costs?",
    ],
}

FAKE_NO_CONFLICTS_RESPONSE: dict[str, Any] = {
    "conflicts": [],
    "open_questions": [],
}


def _make_mock_llm(response_data: dict[str, Any]) -> MagicMock:
    """Return a mock LLM whose ainvoke returns the given response data."""
    mock_response = MagicMock()
    mock_response.content = json.dumps(response_data)

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    return mock_llm


SAMPLE_EXPERT_OUTPUTS: dict[str, Any] = {
    "financial_analyst": {
        "expert_role": "financial_analyst",
        "option_analyses": {
            "Option A": {
                "option": "Option A",
                "claims": ["Low cost"],
                "numbers": {"annual_cost": 50000},
                "risks": ["Market volatility"],
                "score": 8.0,
            },
        },
        "assumptions": ["Stable market conditions"],
        "sources": ["Report 2024"],
        "confidence": 0.85,
    },
    "engineer": {
        "expert_role": "engineer",
        "option_analyses": {
            "Option A": {
                "option": "Option A",
                "claims": ["High implementation effort"],
                "numbers": {"annual_cost": 72000},
                "risks": ["Technical debt"],
                "score": 6.0,
            },
        },
        "assumptions": ["Team has relevant experience"],
        "sources": ["Internal review"],
        "confidence": 0.75,
    },
}


class TestConflictDetectorNode:
    """Test conflict_detector_node with a mocked LLM."""

    @pytest.mark.asyncio
    @patch("decision.nodes.conflict_detector._get_detector_llm")
    async def test_returns_conflicts_when_found(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm(FAKE_CONFLICTS_RESPONSE)

        state = {"expert_outputs": SAMPLE_EXPERT_OUTPUTS}
        result = await conflict_detector_node(state)

        assert "conflicts" in result
        assert len(result["conflicts"]) == 2
        assert result["conflicts"][0]["conflict_type"] == "numeric"
        assert result["conflicts"][1]["conflict_type"] == "assumption_mismatch"

    @pytest.mark.asyncio
    @patch("decision.nodes.conflict_detector._get_detector_llm")
    async def test_returns_open_questions_when_found(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm(FAKE_CONFLICTS_RESPONSE)

        state = {"expert_outputs": SAMPLE_EXPERT_OUTPUTS}
        result = await conflict_detector_node(state)

        assert "open_questions" in result
        assert len(result["open_questions"]) == 2

    @pytest.mark.asyncio
    @patch("decision.nodes.conflict_detector._get_detector_llm")
    async def test_phase_is_conflict(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm(FAKE_CONFLICTS_RESPONSE)

        state = {"expert_outputs": SAMPLE_EXPERT_OUTPUTS}
        result = await conflict_detector_node(state)

        assert result["phase"] == "conflict"

    @pytest.mark.asyncio
    @patch("decision.nodes.conflict_detector._get_detector_llm")
    async def test_no_conflicts_returns_empty_lists(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm(FAKE_NO_CONFLICTS_RESPONSE)

        state = {"expert_outputs": SAMPLE_EXPERT_OUTPUTS}
        result = await conflict_detector_node(state)

        assert result["conflicts"] == []
        assert result["open_questions"] == []
        assert result["phase"] == "conflict"

    @pytest.mark.asyncio
    @patch("decision.nodes.conflict_detector._get_detector_llm")
    async def test_works_with_empty_expert_outputs(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm(FAKE_NO_CONFLICTS_RESPONSE)

        state = {"expert_outputs": {}}
        result = await conflict_detector_node(state)

        assert result["conflicts"] == []
        assert result["open_questions"] == []
        assert result["phase"] == "conflict"

    @pytest.mark.asyncio
    @patch("decision.nodes.conflict_detector._get_detector_llm")
    async def test_works_with_missing_expert_outputs(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm(FAKE_NO_CONFLICTS_RESPONSE)

        state = {}
        result = await conflict_detector_node(state)

        assert result["phase"] == "conflict"

    @pytest.mark.asyncio
    @patch("decision.nodes.conflict_detector._get_detector_llm")
    async def test_llm_receives_serialised_expert_outputs(self, mock_get_llm: MagicMock):
        mock_llm = _make_mock_llm(FAKE_NO_CONFLICTS_RESPONSE)
        mock_get_llm.return_value = mock_llm

        state = {"expert_outputs": SAMPLE_EXPERT_OUTPUTS}
        await conflict_detector_node(state)

        call_args = mock_llm.ainvoke.call_args
        messages = call_args[0][0]
        human_msg_content = messages[1].content

        assert "financial_analyst" in human_msg_content
        assert "engineer" in human_msg_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
