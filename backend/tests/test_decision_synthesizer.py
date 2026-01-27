"""Tests for the synthesizer node of the decision assistant graph."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from decision.nodes.synthesizer import (
    SYNTHESIZER_SYSTEM_PROMPT,
    synthesizer_node,
)


# ---------------------------------------------------------------------------
# System prompt tests
# ---------------------------------------------------------------------------


class TestSynthesizerSystemPrompt:
    """Validate that the prompt enforces comparison -- not summarisation."""

    def test_contains_compare_or_tradeoff(self):
        lower = SYNTHESIZER_SYSTEM_PROMPT.lower()
        assert "compare" in lower or "tradeoff" in lower

    def test_does_not_contain_summariz(self):
        lower = SYNTHESIZER_SYSTEM_PROMPT.lower()
        assert "summariz" not in lower, (
            "The synthesizer prompt must NOT contain the word 'summariz' "
            "(e.g. summarize, summarizer) -- it is a comparator, not a summariser"
        )

    def test_mentions_head_to_head(self):
        lower = SYNTHESIZER_SYSTEM_PROMPT.lower()
        assert "head-to-head" in lower or "head to head" in lower

    def test_mentions_tradeoffs(self):
        assert "tradeoffs" in SYNTHESIZER_SYSTEM_PROMPT

    def test_mentions_pros_and_cons(self):
        lower = SYNTHESIZER_SYSTEM_PROMPT.lower()
        assert "pros" in lower and "cons" in lower

    def test_mentions_confidence(self):
        assert "confidence" in SYNTHESIZER_SYSTEM_PROMPT

    def test_mentions_what_would_change_mind(self):
        assert "what_would_change_mind" in SYNTHESIZER_SYSTEM_PROMPT

    def test_mentions_falsifiable(self):
        lower = SYNTHESIZER_SYSTEM_PROMPT.lower()
        assert "falsifiable" in lower

    def test_mentions_json_output(self):
        assert "JSON" in SYNTHESIZER_SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# synthesizer_node tests (LLM mocked)
# ---------------------------------------------------------------------------


FAKE_RECOMMENDATION: dict[str, Any] = {
    "recommended_option": "Option A",
    "reasoning": [
        "Option A scores 8.0 from financial analyst vs 6.5 for Option B",
        "Annual cost of $50k is 37.5% lower than Option B's $80k",
    ],
    "tradeoffs": {
        "Option A": {
            "pros": ["Lower cost", "Higher ROI"],
            "cons": ["Market volatility risk"],
        },
        "Option B": {
            "pros": ["Premium support", "Established vendor"],
            "cons": ["Higher annual cost", "Vendor lock-in risk"],
        },
    },
    "risks": [
        "Market volatility could reduce ROI",
        "Regulatory changes may affect both options",
    ],
    "what_would_change_mind": [
        "If Option A annual cost exceeds $75k",
        "If Option B vendor offers 30%+ discount",
    ],
    "confidence": 0.78,
}


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
            "Option B": {
                "option": "Option B",
                "claims": ["Premium support"],
                "numbers": {"annual_cost": 80000},
                "risks": ["Vendor lock-in"],
                "score": 6.5,
            },
        },
        "assumptions": ["Stable market"],
        "sources": ["Report 2024"],
        "confidence": 0.85,
    },
}

SAMPLE_CONFLICTS: list[dict[str, Any]] = [
    {
        "conflict_type": "numeric",
        "topic": "annual_cost for Option A",
        "experts": ["financial_analyst", "engineer"],
        "values": ["50000", "72000"],
    },
]


def _make_mock_llm(response_data: dict[str, Any]) -> MagicMock:
    """Return a mock LLM whose ainvoke returns the given response data."""
    mock_response = MagicMock()
    mock_response.content = json.dumps(response_data)

    mock_llm = MagicMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)
    return mock_llm


class TestSynthesizerNode:
    """Test synthesizer_node with a mocked LLM."""

    @pytest.mark.asyncio
    @patch("decision.nodes.synthesizer._get_synthesizer_llm")
    async def test_returns_recommendation_dict(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm(FAKE_RECOMMENDATION)

        state = {
            "expert_outputs": SAMPLE_EXPERT_OUTPUTS,
            "conflicts": SAMPLE_CONFLICTS,
            "human_feedback": None,
        }
        result = await synthesizer_node(state)

        assert "recommendation" in result
        rec = result["recommendation"]
        assert rec["recommended_option"] == "Option A"
        assert isinstance(rec["reasoning"], list)
        assert len(rec["reasoning"]) > 0

    @pytest.mark.asyncio
    @patch("decision.nodes.synthesizer._get_synthesizer_llm")
    async def test_phase_is_done(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm(FAKE_RECOMMENDATION)

        state = {
            "expert_outputs": SAMPLE_EXPERT_OUTPUTS,
            "conflicts": SAMPLE_CONFLICTS,
            "human_feedback": None,
        }
        result = await synthesizer_node(state)

        assert result["phase"] == "done"

    @pytest.mark.asyncio
    @patch("decision.nodes.synthesizer._get_synthesizer_llm")
    async def test_recommendation_has_tradeoffs(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm(FAKE_RECOMMENDATION)

        state = {
            "expert_outputs": SAMPLE_EXPERT_OUTPUTS,
            "conflicts": [],
            "human_feedback": None,
        }
        result = await synthesizer_node(state)

        rec = result["recommendation"]
        assert "Option A" in rec["tradeoffs"]
        assert "Option B" in rec["tradeoffs"]
        assert "pros" in rec["tradeoffs"]["Option A"]
        assert "cons" in rec["tradeoffs"]["Option A"]

    @pytest.mark.asyncio
    @patch("decision.nodes.synthesizer._get_synthesizer_llm")
    async def test_recommendation_has_what_would_change_mind(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm(FAKE_RECOMMENDATION)

        state = {
            "expert_outputs": SAMPLE_EXPERT_OUTPUTS,
            "conflicts": [],
            "human_feedback": None,
        }
        result = await synthesizer_node(state)

        rec = result["recommendation"]
        assert "what_would_change_mind" in rec
        assert isinstance(rec["what_would_change_mind"], list)
        assert len(rec["what_would_change_mind"]) > 0

    @pytest.mark.asyncio
    @patch("decision.nodes.synthesizer._get_synthesizer_llm")
    async def test_recommendation_has_confidence(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm(FAKE_RECOMMENDATION)

        state = {
            "expert_outputs": SAMPLE_EXPERT_OUTPUTS,
            "conflicts": [],
            "human_feedback": None,
        }
        result = await synthesizer_node(state)

        rec = result["recommendation"]
        assert "confidence" in rec
        assert 0.0 <= rec["confidence"] <= 1.0

    @pytest.mark.asyncio
    @patch("decision.nodes.synthesizer._get_synthesizer_llm")
    async def test_includes_human_feedback_in_llm_input(self, mock_get_llm: MagicMock):
        mock_llm = _make_mock_llm(FAKE_RECOMMENDATION)
        mock_get_llm.return_value = mock_llm

        feedback = {
            "action": "proceed",
            "additional_instructions": "Prefer lower cost options",
        }
        state = {
            "expert_outputs": SAMPLE_EXPERT_OUTPUTS,
            "conflicts": [],
            "human_feedback": feedback,
        }
        await synthesizer_node(state)

        call_args = mock_llm.ainvoke.call_args
        messages = call_args[0][0]
        human_msg_content = messages[1].content

        assert "Prefer lower cost options" in human_msg_content

    @pytest.mark.asyncio
    @patch("decision.nodes.synthesizer._get_synthesizer_llm")
    async def test_works_with_empty_state(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm(FAKE_RECOMMENDATION)

        state = {}
        result = await synthesizer_node(state)

        assert "recommendation" in result
        assert result["phase"] == "done"

    @pytest.mark.asyncio
    @patch("decision.nodes.synthesizer._get_synthesizer_llm")
    async def test_recommendation_has_risks(self, mock_get_llm: MagicMock):
        mock_get_llm.return_value = _make_mock_llm(FAKE_RECOMMENDATION)

        state = {
            "expert_outputs": SAMPLE_EXPERT_OUTPUTS,
            "conflicts": [],
            "human_feedback": None,
        }
        result = await synthesizer_node(state)

        rec = result["recommendation"]
        assert "risks" in rec
        assert isinstance(rec["risks"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
