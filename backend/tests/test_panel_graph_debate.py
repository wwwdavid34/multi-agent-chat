import pytest

import panel_graph


class _DummyResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class _DummyModerator:
    def __init__(self, content: str) -> None:
        self._content = content

    async def ainvoke(self, messages):  # noqa: ANN001 - test stub
        return _DummyResponse(self._content)


@pytest.mark.asyncio
async def test_consensus_checker_single_panelist_increments_and_records_history():
    original_history = []
    state = {
        "panel_responses": {"Solo": "answer"},
        "debate_round": 0,
        "debate_history": original_history,
    }

    out = await panel_graph.consensus_checker_node(state)

    assert out["consensus_reached"] is True
    assert out["debate_round"] == 1
    assert len(out["debate_history"]) == 1
    assert out["debate_history"][0]["round_number"] == 0
    assert out["debate_history"][0]["panel_responses"] == {"Solo": "answer"}
    assert out["debate_history"][0]["consensus_reached"] is True

    # Ensure the input list isn't mutated (function should work on a copy).
    assert original_history == []


@pytest.mark.asyncio
async def test_single_panelist_routing_reaches_moderator_without_loop():
    # Simulate a single-panelist debate-mode run without executing any LLM calls.
    state = {
        "debate_mode": True,
        "max_debate_rounds": 3,
        "debate_round": 0,
        "consensus_reached": False,
        "panel_responses": {"Solo": "answer"},
        "debate_history": [],
        "step_review": False,
    }

    assert panel_graph.should_continue_debate(state) == "consensus_checker"

    out = await panel_graph.consensus_checker_node(state)
    state = {**state, **out}

    # Debate mode forces at least one debate round; this must still be finite.
    assert panel_graph.after_consensus_check(state) == "panelists"

    # After the forced round, consensus_reached remains True and should_continue routes to moderator.
    assert panel_graph.should_continue_debate(state) == "moderator"


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ({"debate_mode": False}, "moderator"),
        ({"debate_mode": True, "debate_round": 0}, "consensus_checker"),
        ({"debate_mode": True, "debate_round": 2, "consensus_reached": True}, "moderator"),
        ({"debate_mode": True, "debate_round": 2, "max_debate_rounds": 3, "consensus_reached": False}, "consensus_checker"),
        ({"debate_mode": True, "debate_round": 4, "max_debate_rounds": 3, "consensus_reached": False}, "moderator"),
    ],
)
def test_should_continue_debate_routes_correctly(state, expected):
    assert panel_graph.should_continue_debate(state) == expected


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        # Force at least one debate round (round 0 initial → consensus check increments to 1).
        ({"debate_round": 1, "consensus_reached": True, "max_debate_rounds": 3, "step_review": False}, "panelists"),
        ({"debate_round": 1, "consensus_reached": False, "max_debate_rounds": 3, "step_review": True}, "pause_for_review"),
        # After round 1+, consensus can end the debate.
        ({"debate_round": 2, "consensus_reached": True, "max_debate_rounds": 3, "step_review": False}, "moderator"),
        # Max rounds cap ends debate after evaluation increments debate_round beyond max.
        ({"debate_round": 4, "consensus_reached": False, "max_debate_rounds": 3, "step_review": False}, "moderator"),
        # Step review pauses when debate continues.
        ({"debate_round": 2, "consensus_reached": False, "max_debate_rounds": 3, "step_review": True}, "pause_for_review"),
        # Otherwise continue debating.
        ({"debate_round": 2, "consensus_reached": False, "max_debate_rounds": 3, "step_review": False}, "panelists"),
    ],
)
def test_after_consensus_check_routes_correctly(state, expected):
    assert panel_graph.after_consensus_check(state) == expected


@pytest.mark.asyncio
async def test_consensus_checker_parses_yes_and_updates_history(monkeypatch):
    monkeypatch.setattr(panel_graph, "moderator_model", _DummyModerator("CONSENSUS: yes\nREASONING: ok\nKEY_DISAGREEMENTS: none"))

    original_history = [{"round_number": 0, "panel_responses": {"A": "x"}, "consensus_reached": False}]
    state = {
        "panel_responses": {"A": "x", "B": "y"},
        "debate_round": 1,
        "debate_history": original_history,
    }

    out = await panel_graph.consensus_checker_node(state)

    assert out["consensus_reached"] is True
    assert out["debate_round"] == 2
    assert len(out["debate_history"]) == 2
    assert out["debate_history"][-1]["round_number"] == 1
    assert out["debate_history"][-1]["panel_responses"] == {"A": "x", "B": "y"}
    assert out["debate_history"][-1]["consensus_reached"] is True

    # Ensure the input list isn't mutated.
    assert len(original_history) == 1


@pytest.mark.asyncio
async def test_max_round_cap_still_evaluates_final_round(monkeypatch):
    # When debate_round == max_debate_rounds, panelists already produced "final round" responses.
    # We must still route to consensus_checker so the final round is evaluated/recorded.
    monkeypatch.setattr(panel_graph, "moderator_model", _DummyModerator("CONSENSUS: NO\nREASONING: disagree\nKEY_DISAGREEMENTS: x"))

    state = {
        "debate_mode": True,
        "max_debate_rounds": 3,
        "debate_round": 3,
        "consensus_reached": False,
        "panel_responses": {"A": "x", "B": "y"},
        "debate_history": [],
        "step_review": False,
    }

    assert panel_graph.should_continue_debate(state) == "consensus_checker"

    out = await panel_graph.consensus_checker_node(state)
    assert out["debate_round"] == 4
    assert out["debate_history"][-1]["round_number"] == 3

    state = {**state, **out}
    assert panel_graph.after_consensus_check(state) == "moderator"

