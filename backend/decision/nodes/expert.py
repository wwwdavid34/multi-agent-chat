"""Expert node for the decision assistant graph.

Each expert is dispatched in parallel via LangGraph's ``Send()`` API.
The planner produces expert tasks and ``fan_out_experts`` maps each one
to a ``Send("run_expert", ...)`` invocation.  Each expert runs an
agentic tool-calling loop with access to web search and a calculator.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Send

from decision.schemas import ExpertOutput, ExpertTask, OptionAnalysis
from decision.tools.calculator import create_calculator_tool
from decision.tools.search import create_search_tool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

EXPERT_SYSTEM_PROMPT = """\
You are a domain expert with the role: {role}.

You are analysing the following decision options:
{options}

Constraints to respect:
{constraints}

Your deliverable: {deliverable}

Rules:
1. Analyse each option thoroughly using data and reasoning.
2. You MUST commit to specific numbers -- never use ranges or say "it depends".
3. State every assumption explicitly; do not hedge or equivocate.
4. Rate each option from 0-10 with a concrete score.
5. Cite sources for any factual claims.
6. Never hedge -- take a clear position on each option.

Output ONLY valid JSON matching this schema:
{{
  "expert_role": "<your role>",
  "option_analyses": {{
    "<option_name>": {{
      "option": "<option_name>",
      "claims": ["<claim1>", ...],
      "numbers": {{"<metric>": <value>, ...}},
      "risks": ["<risk1>", ...],
      "score": <0-10>
    }}
  }},
  "assumptions": ["<assumption1>", ...],
  "sources": ["<source1>", ...],
  "confidence": <0.0-1.0>
}}
"""

# Maximum number of tool-calling rounds before forcing a final answer
_MAX_TOOL_ROUNDS = 5


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------


def _get_expert_llm() -> ChatOpenAI:
    """Return the LLM instance used by expert nodes."""
    return ChatOpenAI(model="gpt-4o", temperature=0.3)


# ---------------------------------------------------------------------------
# Fan-out: create one Send per expert task
# ---------------------------------------------------------------------------


def fan_out_experts(state: dict) -> list[Send]:
    """Map each expert task in state to a ``Send("run_expert", ...)`` object.

    Reads ``expert_tasks``, ``decision_options``, and ``constraints``
    from *state* and returns a list of ``Send`` objects that LangGraph
    will dispatch in parallel.
    """
    expert_tasks: list[dict | ExpertTask] = state.get("expert_tasks", [])
    decision_options: list[str] = state.get("decision_options", [])
    constraints: dict[str, Any] = state.get("constraints", {})

    sends: list[Send] = []
    for task in expert_tasks:
        payload: dict[str, Any] = {
            "expert_task": task if isinstance(task, dict) else task.model_dump(),
            "decision_options": decision_options,
            "constraints": constraints,
        }
        sends.append(Send("run_expert", payload))

    return sends


# ---------------------------------------------------------------------------
# Expert agent node (tool-calling loop)
# ---------------------------------------------------------------------------


def _execute_tool(tool_call: dict, tools_by_name: dict) -> ToolMessage:
    """Execute a single tool call and return the resulting ToolMessage."""
    tool_name = tool_call["name"]
    tool_args = tool_call.get("args", {})
    tool_id = tool_call.get("id", "")

    tool_fn = tools_by_name.get(tool_name)
    if tool_fn is None:
        content = f"Error: unknown tool '{tool_name}'"
    else:
        try:
            content = tool_fn.invoke(tool_args)
        except Exception as exc:  # noqa: BLE001
            content = f"Error executing {tool_name}: {exc}"

    return ToolMessage(content=str(content), tool_call_id=tool_id)


async def run_expert(state: dict) -> dict:
    """Run a single expert's tool-calling agent loop.

    The node:
    1. Formats the system prompt with the expert's role and deliverable.
    2. Binds web-search and calculator tools to the LLM.
    3. Runs up to ``_MAX_TOOL_ROUNDS`` iterations, executing any tool
       calls the model requests.
    4. Parses the final response as JSON into an ``ExpertOutput``.
    5. Returns ``{"expert_outputs": {role: output.model_dump()}}``.
    """
    # -- Extract and normalise the expert task --------------------------------
    raw_task = state.get("expert_task", {})
    if isinstance(raw_task, dict):
        task = ExpertTask(**raw_task)
    else:
        task = raw_task

    decision_options: list[str] = state.get("decision_options", [])
    constraints: dict[str, Any] = state.get("constraints", {})

    role = task.expert_role
    deliverable = task.deliverable

    # -- Format the system prompt ---------------------------------------------
    options_text = "\n".join(f"- {opt}" for opt in decision_options)
    constraints_text = json.dumps(constraints) if constraints else "None specified"

    system_content = EXPERT_SYSTEM_PROMPT.format(
        role=role,
        options=options_text,
        constraints=constraints_text,
        deliverable=deliverable,
    )

    # -- Set up LLM with tools ------------------------------------------------
    search_tool = create_search_tool()
    calc_tool = create_calculator_tool()
    tools = [search_tool, calc_tool]
    tools_by_name = {t.name: t for t in tools}

    llm = _get_expert_llm()
    llm_with_tools = llm.bind_tools(tools)

    # -- Build initial messages ------------------------------------------------
    messages: list = [
        SystemMessage(content=system_content),
        HumanMessage(
            content=(
                f"Please analyse the decision options as the {role} expert. "
                f"Use the available tools if needed, then produce your final "
                f"JSON output."
            )
        ),
    ]

    # -- Agent loop: invoke LLM, handle tool calls ----------------------------
    final_response: AIMessage | None = None

    for _round in range(_MAX_TOOL_ROUNDS):
        response: AIMessage = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            final_response = response
            break

        # Execute each tool call and feed results back
        for tc in tool_calls:
            tool_msg = _execute_tool(tc, tools_by_name)
            messages.append(tool_msg)
    else:
        # Exhausted all rounds -- use the last response as final
        final_response = messages[-1] if messages else None

    # -- Parse JSON output -----------------------------------------------------
    try:
        content = final_response.content if final_response else ""
        # Strip markdown code fences if present
        text = content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

        parsed = json.loads(text)
        output = ExpertOutput(**parsed)
    except Exception:
        logger.warning("Failed to parse expert output for role=%s, returning minimal output", role)
        # Return a minimal, low-confidence output so the pipeline continues
        minimal_analyses = {
            opt: OptionAnalysis(
                option=opt,
                claims=["Analysis failed -- unable to parse expert response"],
                score=0.0,
            )
            for opt in decision_options
        }
        output = ExpertOutput(
            expert_role=role,
            option_analyses=minimal_analyses,
            assumptions=["Parse error -- expert output was not valid JSON"],
            sources=[],
            confidence=0.0,
        )

    return {"expert_outputs": {role: output.model_dump()}}
