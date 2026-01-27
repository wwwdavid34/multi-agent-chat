"""Human gate node for the decision assistant graph.

This node pauses graph execution using LangGraph's ``interrupt()``
mechanism, presenting the current analysis state to a human reviewer.
When the graph is resumed, the human's feedback is captured and the
routing function decides whether to loop back to the experts or
proceed to synthesis.
"""

from __future__ import annotations

from typing import Any

from langgraph.types import interrupt

from decision.state import DecisionState


# ---------------------------------------------------------------------------
# Human gate node
# ---------------------------------------------------------------------------


async def human_gate_node(state: DecisionState) -> dict[str, Any]:
    """Pause the graph and present analysis state to a human reviewer.

    Calls ``interrupt()`` with the current decision options, expert
    outputs, conflicts, and open questions.  When the graph is resumed
    with a value, that value becomes the ``human_feedback`` field.
    The iteration counter is incremented by one.
    """
    interrupt_payload = {
        "decision_options": state.get("decision_options", []),
        "expert_outputs": state.get("expert_outputs", {}),
        "conflicts": state.get("conflicts", []),
        "open_questions": state.get("open_questions", []),
    }

    resumed_value = interrupt(value=interrupt_payload)

    # Normalise: if the resumed value is not a dict, wrap it
    if not isinstance(resumed_value, dict):
        resumed_value = {"action": "proceed"}

    current_iteration: int = state.get("iteration", 0)

    return {
        "human_feedback": resumed_value,
        "iteration": current_iteration + 1,
        "phase": "human",
    }


# ---------------------------------------------------------------------------
# Routing function (pure -- no LLM)
# ---------------------------------------------------------------------------


def route_after_human(state: DecisionState) -> str:
    """Decide the next node after the human gate.

    Returns:
        ``"synthesizer"`` if the human approved or we have exhausted
        iterations; ``"fan_out_experts"`` if re-analysis is requested
        and the iteration budget allows.
    """
    feedback: Any = state.get("human_feedback")

    # No feedback at all -> proceed to synthesis
    if feedback is None:
        return "synthesizer"

    # Extract action -- handle both dict and object with .action
    if isinstance(feedback, dict):
        action = feedback.get("action", "proceed")
    else:
        action = getattr(feedback, "action", "proceed")

    if action == "re_analyze":
        iteration: int = state.get("iteration", 0)
        max_iterations: int = state.get("max_iterations", 3)
        if iteration < max_iterations:
            return "fan_out_experts"

    return "synthesizer"
