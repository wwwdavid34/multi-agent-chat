"""LangGraph state definition for the decision assistant.

DecisionState is a TypedDict consumed by every graph node.  The
``expert_outputs`` field uses a custom reducer so that parallel expert
nodes can each write their own key without clobbering one another.
"""

from __future__ import annotations

from typing import Annotated, Any, TypedDict

from decision.schemas import (
    Conflict,
    ExpertOutput,
    ExpertTask,
    HumanFeedback,
    Recommendation,
)


def merge_expert_outputs(
    existing: dict[str, ExpertOutput] | None,
    new: dict[str, ExpertOutput] | None,
) -> dict[str, ExpertOutput]:
    """Reducer that merges expert output dicts instead of replacing.

    LangGraph calls this with the current value and the incoming update.
    We merge so that parallel expert nodes each contribute their key.
    """
    merged: dict[str, ExpertOutput] = {}
    if existing:
        merged.update(existing)
    if new:
        merged.update(new)
    return merged


class DecisionState(TypedDict, total=False):
    """Shared state passed through every node of the decision graph.

    ``total=False`` makes all fields optional so nodes only need to
    write the keys they care about.
    """

    # User input
    user_question: str
    constraints: dict[str, Any]

    # Planner outputs
    decision_options: list[str]
    expert_tasks: list[ExpertTask]

    # Expert outputs (merged via reducer)
    expert_outputs: Annotated[dict[str, ExpertOutput], merge_expert_outputs]

    # Conflict detection
    conflicts: list[Conflict]
    open_questions: list[str]

    # Human gate
    human_feedback: HumanFeedback

    # Iteration control
    iteration: int
    max_iterations: int

    # Final output
    recommendation: Recommendation

    # Phase tracking
    phase: str
