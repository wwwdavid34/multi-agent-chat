"""Planner node for the decision assistant graph.

The planner decomposes a user's decision question into concrete options
and a set of expert tasks.  It is the first node executed in the graph.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage

from decision.state import DecisionState

PLANNER_SYSTEM_PROMPT = """\
You are a decision-planning assistant.  Given a decision question and
optional constraints, decompose the problem into:

1. **decision_options** -- a list of 2-5 concrete options the user can choose from.
2. **expert_tasks** -- a list of 2-5 expert analysis tasks.  Each task is an object
   with "expert_role" (a short domain-expert title) and "deliverable" (a specific,
   measurable deliverable the expert must produce).

Rules:
- Always propose between 2 and 5 decision options.
- Always propose between 2 and 5 expert roles.
- Each expert must have a specific deliverable -- never a vague instruction.
- Output ONLY valid JSON with exactly two top-level keys:
  "decision_options" (list of strings) and "expert_tasks" (list of objects with
  "expert_role" and "deliverable" string fields).
- Do NOT include any text outside the JSON object.
"""


def _get_planner_llm() -> ChatOpenAI:
    """Return the LLM instance used by the planner node."""
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0.2,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


async def planner_node(state: DecisionState) -> dict[str, Any]:
    """Decompose a decision question into options and expert tasks.

    Reads ``user_question`` and ``constraints`` from *state*, calls the
    planner LLM, and returns a dict with ``decision_options``,
    ``expert_tasks`` (list of dicts), and ``phase`` set to ``"analysis"``.
    """
    user_question: str = state.get("user_question", "")
    constraints: dict[str, Any] = state.get("constraints", {})

    # Build the human message
    content_parts = [f"Decision question: {user_question}"]
    if constraints:
        content_parts.append(f"Constraints: {json.dumps(constraints)}")
    human_content = "\n".join(content_parts)

    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=human_content),
    ]

    llm = _get_planner_llm()
    response = await llm.ainvoke(messages)

    parsed: dict[str, Any] = json.loads(response.content)

    decision_options: list[str] = parsed["decision_options"]
    expert_tasks: list[dict[str, str]] = parsed["expert_tasks"]

    return {
        "decision_options": decision_options,
        "expert_tasks": expert_tasks,
        "phase": "analysis",
    }
