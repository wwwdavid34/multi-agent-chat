"""Synthesizer node for the decision assistant graph.

Produces the final recommendation by performing head-to-head comparison
of all decision options.  This is NOT a summarizer -- it actively
compares options against each other, weighing expert evidence, conflicts,
and human feedback to arrive at a justified recommendation.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI

from decision.schemas import Recommendation
from decision.state import DecisionState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYNTHESIZER_SYSTEM_PROMPT = """\
You are a decision-synthesis analyst.  Your job is to compare options
head-to-head, weigh expert evidence, and produce a clear Recommendation.

You are NOT a text condenser.  You must actively compare and evaluate
every option against the others, using concrete data from the expert
analyses.  For each pair of options, identify the tradeoff and explain
which expert data points drive the comparison.

Rules:
1. Every option MUST appear in the "tradeoffs" dict with BOTH "pros"
   AND "cons" lists -- no option may have an empty pros or cons list.
2. Your "reasoning" list must reference specific expert data (numbers,
   claims, scores) -- never make unsupported assertions.
3. The "what_would_change_mind" list must contain only falsifiable
   conditions -- concrete, measurable thresholds that would reverse
   the recommendation (e.g. "if annual cost exceeds $80k" rather
   than vague statements).
4. "confidence" must reflect the degree of certainty: high agreement
   among experts and few conflicts -> higher confidence; many
   unresolved conflicts or missing data -> lower confidence.
5. If human feedback is provided, incorporate it: respect removed
   options, updated constraints, and additional instructions.
6. Address each conflict explicitly -- state which side you chose
   and why, referencing the expert evidence.

Output ONLY valid JSON matching this schema:
{
  "recommended_option": "<option name>",
  "reasoning": ["<reason1>", ...],
  "tradeoffs": {
    "<option_name>": {
      "pros": ["<pro1>", ...],
      "cons": ["<con1>", ...]
    }
  },
  "risks": ["<risk1>", ...],
  "what_would_change_mind": ["<condition1>", ...],
  "confidence": <0.0-1.0>
}
"""

# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------


def _get_synthesizer_llm() -> ChatOpenAI:
    """Return the LLM instance used by the synthesizer node."""
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0.2,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


# ---------------------------------------------------------------------------
# Node function
# ---------------------------------------------------------------------------


async def synthesizer_node(state: DecisionState) -> dict[str, Any]:
    """Produce a final recommendation via head-to-head option comparison.

    Reads ``expert_outputs``, ``conflicts``, and ``human_feedback``
    from *state*, invokes the synthesizer LLM, parses the response
    into a ``Recommendation``, and returns it along with
    ``phase`` set to ``"done"``.
    """
    expert_outputs: dict = state.get("expert_outputs", {})
    conflicts: list = state.get("conflicts", [])
    human_feedback: Any = state.get("human_feedback")

    # Build input sections for the LLM
    sections: list[str] = []

    sections.append("## Expert Outputs\n")
    sections.append(json.dumps(expert_outputs, indent=2, default=str))

    sections.append("\n## Conflicts Detected\n")
    sections.append(json.dumps(conflicts, indent=2, default=str))

    if human_feedback is not None:
        sections.append("\n## Human Feedback\n")
        if isinstance(human_feedback, dict):
            sections.append(json.dumps(human_feedback, indent=2, default=str))
        else:
            sections.append(json.dumps(
                human_feedback.model_dump() if hasattr(human_feedback, "model_dump") else str(human_feedback),
                indent=2,
                default=str,
            ))

    human_content = "\n".join(sections)

    messages = [
        SystemMessage(content=SYNTHESIZER_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                "Compare the following options head-to-head and produce "
                "your Recommendation:\n\n" + human_content
            )
        ),
    ]

    llm = _get_synthesizer_llm()
    response = await llm.ainvoke(messages)

    parsed: dict[str, Any] = json.loads(response.content)
    recommendation = Recommendation(**parsed)

    return {
        "recommendation": recommendation.model_dump(),
        "phase": "done",
    }
