"""Expert node for the decision assistant graph.

Each expert is dispatched in parallel via LangGraph's ``Send()`` API.
The planner produces expert tasks and ``fan_out_experts`` maps each one
to a ``Send("run_expert", ...)`` invocation.  Each expert runs an
agentic tool-calling loop with access to web search and a calculator.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.types import Send

from config import get_claude_api_key, get_gemini_api_key, get_openai_api_key
from decision.rate_limiter import get_rate_limiter
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

# Conservative per-call token estimate for rate-limiter reservation.
# Covers system prompt (~800) + messages (~1200) + completion (~2000).
_ESTIMATED_TOKENS_PER_CALL = 4000


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------


def _resolve_key(provider: str, provider_keys: dict[str, str]) -> str:
    """Resolve an API key: request-provided first, then env var fallback."""
    key = provider_keys.get(provider)
    if key:
        return key
    fallbacks = {"openai": get_openai_api_key, "claude": get_claude_api_key, "gemini": get_gemini_api_key}
    getter = fallbacks.get(provider)
    if getter:
        return getter()
    raise ValueError(f"No API key for provider: {provider}")


def _create_expert_llm(
    provider: str, model: str, provider_keys: dict[str, str]
) -> BaseChatModel:
    """Create an LLM instance for the given provider/model."""
    api_key = _resolve_key(provider, provider_keys)

    if provider == "openai":
        return ChatOpenAI(model=model, temperature=0.3, api_key=api_key)
    elif provider == "claude":
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(model=model, temperature=0.3, anthropic_api_key=api_key)
    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(model=model, google_api_key=api_key, temperature=0.3)
    else:
        raise ValueError(f"Unsupported expert provider: {provider}")


def _get_default_expert_llm() -> ChatOpenAI:
    """Fallback: return the default gpt-4o LLM for experts."""
    return ChatOpenAI(model="gpt-4o", temperature=0.3)


# ---------------------------------------------------------------------------
# Fan-out: create one Send per expert task
# ---------------------------------------------------------------------------


def fan_out_experts(state: dict) -> list[Send]:
    """Map each expert task in state to a ``Send("run_expert", ...)`` object.

    Reads ``expert_tasks``, ``decision_options``, ``constraints``,
    ``available_models``, and ``provider_keys`` from *state*.
    Assigns models to experts via round-robin to spread load across
    providers and avoid single-provider TPM rate limits.
    """
    expert_tasks: list[dict | ExpertTask] = state.get("expert_tasks", [])
    decision_options: list[str] = state.get("decision_options", [])
    constraints: dict[str, Any] = state.get("constraints", {})
    available_models: list[dict[str, str]] = state.get("available_models", [])
    provider_keys: dict[str, str] = state.get("provider_keys", {})

    # Fallback to default gpt-4o if no eligible models provided
    if not available_models:
        available_models = [{"provider": "openai", "model": "gpt-4o"}]

    logger.info(
        "Fan-out %d experts across %d model(s): %s",
        len(expert_tasks),
        len(available_models),
        [f"{m['provider']}/{m['model']}" for m in available_models],
    )

    sends: list[Send] = []
    for i, task in enumerate(expert_tasks):
        model_assignment = available_models[i % len(available_models)]
        payload: dict[str, Any] = {
            "expert_task": task if isinstance(task, dict) else task.model_dump(),
            "decision_options": decision_options,
            "constraints": constraints,
            "model_assignment": model_assignment,
            "provider_keys": provider_keys,
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

    model_assignment: dict[str, str] = state.get("model_assignment", {})
    prov_keys: dict[str, str] = state.get("provider_keys", {})

    active_provider = "openai"  # default for rate-limiter tracking
    if model_assignment:
        active_provider = model_assignment["provider"]
        model_name = model_assignment["model"]
        try:
            llm = _create_expert_llm(active_provider, model_name, prov_keys)
            logger.info("Expert '%s' using %s/%s", role, active_provider, model_name)
        except Exception:
            logger.warning(
                "Failed to create %s/%s for expert '%s', falling back to gpt-4o",
                active_provider, model_name, role, exc_info=True,
            )
            llm = _get_default_expert_llm()
            active_provider = "openai"
    else:
        llm = _get_default_expert_llm()

    llm_with_tools = llm.bind_tools(tools)
    limiter = get_rate_limiter()

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
        # Throttle: wait for TPM headroom before calling the provider
        estimated = _ESTIMATED_TOKENS_PER_CALL
        await limiter.acquire(active_provider, estimated)

        try:
            response: AIMessage = await llm_with_tools.ainvoke(messages)
        except Exception as invoke_exc:
            logger.error("Expert '%s' LLM invoke failed on round %d: %s", role, _round, invoke_exc, exc_info=True)
            break
        messages.append(response)

        # Record actual token usage from response metadata
        usage_meta = getattr(response, "usage_metadata", None)
        if usage_meta and isinstance(usage_meta, dict):
            actual = usage_meta.get("total_tokens", estimated)
        elif usage_meta and hasattr(usage_meta, "total_tokens"):
            actual = usage_meta.total_tokens or estimated
        else:
            actual = estimated
        limiter.record(active_provider, actual, estimated)

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
    raw_content = ""
    try:
        raw_content = final_response.content if final_response else ""

        # Claude returns content as a list of blocks; extract text from them
        if isinstance(raw_content, list):
            raw_content = " ".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in raw_content
            )

        text = raw_content.strip()

        # Try 1: strip markdown code fences
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if fence_match:
            text = fence_match.group(1).strip()

        # Try 2: if it doesn't start with '{', find the first '{' ... last '}'
        if not text.startswith("{"):
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end > start:
                text = text[start : end + 1]

        parsed = json.loads(text)
        output = ExpertOutput(**parsed)
    except Exception:
        logger.warning(
            "Failed to parse expert output for role=%s, returning minimal output. "
            "Raw content (first 1000 chars): %s",
            role,
            (raw_content[:1000] if raw_content else "<empty>"),
            exc_info=True,
        )
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
