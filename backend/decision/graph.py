"""LangGraph StateGraph assembly for the decision assistant.

Wires together all nodes -- planner, parallel experts (via ``Send()``),
conflict detector, human gate (with ``interrupt()``), and synthesizer --
into a compiled graph with conditional routing and a checkpointer for
durable execution.
"""

from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from decision.nodes.conflict_detector import conflict_detector_node
from decision.nodes.expert import fan_out_experts, run_expert
from decision.nodes.human_gate import human_gate_node, route_after_human
from decision.nodes.planner import planner_node
from decision.nodes.synthesizer import synthesizer_node
from decision.state import DecisionState


# ---------------------------------------------------------------------------
# Routing helpers
# ---------------------------------------------------------------------------


def _route_after_conflicts(state: DecisionState) -> str:
    """Route to the human gate if conflicts exist, else straight to synthesis.

    Returns ``"human_gate"`` when ``state["conflicts"]`` is a non-empty
    list, otherwise ``"synthesizer"``.
    """
    conflicts = state.get("conflicts", [])
    if conflicts:
        return "human_gate"
    return "synthesizer"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------


def build_decision_graph(checkpointer=None):
    """Assemble and compile the full decision-assistant StateGraph.

    Parameters
    ----------
    checkpointer : optional
        A LangGraph checkpointer instance.  If *None*, an
        ``InMemorySaver`` is created automatically.

    Returns
    -------
    CompiledGraph
        The compiled LangGraph ready for ``.invoke()`` / ``.ainvoke()``.
    """
    builder = StateGraph(DecisionState)

    # -- Add nodes ------------------------------------------------------------
    builder.add_node("planner", planner_node)
    builder.add_node("run_expert", run_expert)
    builder.add_node("conflict_detector", conflict_detector_node)
    builder.add_node("human_gate", human_gate_node)
    builder.add_node("synthesizer", synthesizer_node)

    # -- Edges ----------------------------------------------------------------

    # Entry -> planner
    builder.add_edge(START, "planner")

    # Planner -> parallel experts via Send()
    builder.add_conditional_edges("planner", fan_out_experts, ["run_expert"])

    # Experts -> conflict detector
    builder.add_edge("run_expert", "conflict_detector")

    # Conflict detector -> conditional: human gate or synthesizer
    builder.add_conditional_edges(
        "conflict_detector",
        _route_after_conflicts,
        {"human_gate": "human_gate", "synthesizer": "synthesizer"},
    )

    # Human gate -> conditional: re-analyse or synthesise
    builder.add_conditional_edges(
        "human_gate",
        route_after_human,
        {"fan_out_experts": "planner", "synthesizer": "synthesizer"},
    )

    # Synthesizer -> END
    builder.add_edge("synthesizer", END)

    # -- Compile --------------------------------------------------------------
    if checkpointer is None:
        checkpointer = InMemorySaver()

    return builder.compile(checkpointer=checkpointer)
