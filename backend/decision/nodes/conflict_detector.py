"""Conflict detector node for the decision assistant graph.

Analyses expert outputs to surface disagreements, data conflicts,
and open questions that need resolution before synthesis.  The node
does NOT attempt to resolve conflicts -- it only identifies them so
the human gate (or the synthesizer) can address them.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from decision.state import DecisionState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

DETECTOR_SYSTEM_PROMPT = """\
You are a conflict-detection analyst.  You receive structured outputs
from multiple domain experts who have each analysed the same set of
decision options.  Your job is to find disagreements between the
experts.  Do NOT resolve conflicts -- only surface them.

Detection rules:
1. Numeric conflict -- two experts provide numbers for the same metric
   that differ by more than 20% (relative to the smaller value).
2. Assumption mismatch -- experts rely on contradictory assumptions.
3. Risk assessment disagreement -- experts disagree on the severity or
   existence of a particular risk.
4. Coverage gap -- an option or dimension that some experts analysed
   but others ignored entirely.

For each conflict found, produce an object with:
- "conflict_type": one of "numeric", "assumption_mismatch",
  "risk_disagreement", "coverage_gap"
- "topic": short label for what the conflict is about
- "experts": list of expert roles involved
- "values": list of the conflicting data points (as strings)

Also produce a list of open questions -- things that remain unresolved
or ambiguous across the expert outputs.

Output ONLY valid JSON with exactly two top-level keys:
{
  "conflicts": [ ... ],
  "open_questions": [ ... ]
}

If no conflicts are found, return empty lists for both keys.
"""

# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------


def _get_detector_llm() -> ChatOpenAI:
    """Return the LLM instance used by the conflict detector node."""
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0.1,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------


async def conflict_detector_node(state: DecisionState) -> dict[str, Any]:
    """Detect disagreements across expert outputs.

    Reads ``expert_outputs`` from *state*, serialises them to JSON,
    invokes the detector LLM, and returns a dict with ``conflicts``,
    ``open_questions``, and ``phase`` set to ``"conflict"``.
    """
    expert_outputs: dict = state.get("expert_outputs", {})

    # Serialise expert outputs for the LLM
    expert_json = json.dumps(expert_outputs, indent=2, default=str)

    messages = [
        SystemMessage(content=DETECTOR_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                "Here are the expert outputs to analyse for conflicts:\n\n"
                f"{expert_json}"
            )
        ),
    ]

    llm = _get_detector_llm()
    response = await llm.ainvoke(messages)

    parsed: dict[str, Any] = json.loads(response.content)

    conflicts: list[dict] = parsed.get("conflicts", [])
    open_questions: list[str] = parsed.get("open_questions", [])

    return {
        "conflicts": conflicts,
        "open_questions": open_questions,
        "phase": "conflict",
    }
