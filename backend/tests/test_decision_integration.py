"""End-to-end integration test for the decision graph.

Runs the full decision graph with mocked LLMs to verify that
planner -> expert -> conflict detector -> synthesizer wiring works
correctly and produces the expected final state.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from decision.graph import build_decision_graph


def _mock_llm_response(content: dict):
    """Create a mock LLM response with JSON content and no tool calls."""
    resp = MagicMock()
    resp.content = json.dumps(content)
    resp.tool_calls = []
    return resp


@pytest.mark.asyncio
async def test_decision_graph_no_conflicts():
    """Full graph: planner -> 1 expert -> no conflicts -> synthesizer."""
    planner_resp = _mock_llm_response({
        "decision_options": ["Build", "Buy"],
        "expert_tasks": [
            {"expert_role": "Finance", "deliverable": "Cost model"},
        ],
    })

    expert_resp = _mock_llm_response({
        "expert_role": "Finance",
        "option_analyses": {
            "Build": {"option": "Build", "claims": ["Cheap"], "numbers": {}, "risks": [], "score": 7.0},
            "Buy": {"option": "Buy", "claims": ["Fast"], "numbers": {}, "risks": [], "score": 8.0},
        },
        "assumptions": ["Stable market"],
        "sources": [],
        "confidence": 0.8,
    })

    conflict_resp = _mock_llm_response({"conflicts": [], "open_questions": []})

    synth_resp = _mock_llm_response({
        "recommended_option": "Buy",
        "reasoning": ["Faster"],
        "tradeoffs": {"Build": {"pros": ["Control"], "cons": ["Slow"]}, "Buy": {"pros": ["Fast"], "cons": ["Lock-in"]}},
        "risks": ["Vendor risk"],
        "what_would_change_mind": ["Build < 3 months"],
        "confidence": 0.75,
    })

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(side_effect=[planner_resp, expert_resp, conflict_resp, synth_resp])
    mock_llm.bind_tools = MagicMock(return_value=mock_llm)

    with patch("decision.nodes.planner._get_planner_llm", return_value=mock_llm), \
         patch("decision.nodes.expert._get_expert_llm", return_value=mock_llm), \
         patch("decision.nodes.conflict_detector._get_detector_llm", return_value=mock_llm), \
         patch("decision.nodes.synthesizer._get_synthesizer_llm", return_value=mock_llm):

        graph = build_decision_graph()
        config = {"configurable": {"thread_id": "test-integration"}}
        result = await graph.ainvoke(
            {
                "user_question": "Build or buy?",
                "constraints": {},
                "iteration": 0,
                "max_iterations": 2,
                "phase": "planning",
                "expert_outputs": {},
            },
            config,
        )

    assert result["phase"] == "done"
    assert result["recommendation"]["recommended_option"] == "Buy"
    assert len(result["decision_options"]) == 2
    assert "Finance" in result["expert_outputs"]
