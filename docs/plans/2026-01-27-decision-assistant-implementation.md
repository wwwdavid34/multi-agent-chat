# Decision Assistant Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the AG2 debate engine with a LangGraph-based multi-agent decision assistant that decomposes questions, runs parallel expert analysis with tools, detects conflicts, supports human-in-the-loop, and produces structured recommendations.

**Architecture:** Pure LangGraph StateGraph with `Send()` for parallel expert fan-out, `interrupt()` for human gate, `Annotated` reducers for merging expert outputs. SSE streaming to React frontend with a new phase-driven `DecisionViewer`.

**Tech Stack:** LangGraph (already in deps), langchain-openai, langchain-tavily, FastAPI SSE, React + TypeScript + Tailwind

**Design doc:** `docs/plans/2026-01-26-decision-assistant-design.md`

---

## Task 1: Schemas and State

**Files:**
- Create: `backend/decision/__init__.py`
- Create: `backend/decision/schemas.py`
- Create: `backend/decision/state.py`
- Test: `backend/tests/test_decision_schemas.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_decision_schemas.py
import pytest
from decision.schemas import (
    ExpertTask,
    OptionAnalysis,
    ExpertOutput,
    Conflict,
    HumanFeedback,
    Recommendation,
)


def test_expert_task_creation():
    task = ExpertTask(expert_role="Finance", deliverable="5yr cost model")
    assert task.expert_role == "Finance"
    assert task.deliverable == "5yr cost model"


def test_option_analysis_creation():
    analysis = OptionAnalysis(
        option="Build",
        claims=["Lower long-term cost"],
        numbers={"year_1_cost": 500000},
        risks=["Engineering hiring risk"],
        score=7.5,
    )
    assert analysis.score == 7.5
    assert len(analysis.claims) == 1


def test_expert_output_creation():
    analysis = OptionAnalysis(
        option="Build",
        claims=["Claim 1"],
        numbers={"cost": 100},
        risks=["Risk 1"],
        score=6.0,
    )
    output = ExpertOutput(
        expert_role="Finance",
        option_analyses={"Build": analysis},
        assumptions=["Hiring 5 engineers"],
        sources=["https://example.com"],
        confidence=0.8,
    )
    assert output.expert_role == "Finance"
    assert output.confidence == 0.8
    assert "Build" in output.option_analyses


def test_conflict_creation():
    conflict = Conflict(
        conflict_type="numeric",
        topic="TAM",
        experts=["Market", "Finance"],
        values=["$3B", "$900M"],
    )
    assert conflict.conflict_type == "numeric"
    assert len(conflict.experts) == 2


def test_recommendation_creation():
    rec = Recommendation(
        recommended_option="Buy",
        reasoning=["Lower risk", "Faster time to market"],
        tradeoffs={
            "Build": {"pros": ["Full control"], "cons": ["Slow"]},
            "Buy": {"pros": ["Fast"], "cons": ["Vendor lock-in"]},
        },
        risks=["Vendor bankruptcy"],
        what_would_change_mind=["If build timeline < 3 months"],
        confidence=0.72,
    )
    assert rec.recommended_option == "Buy"
    assert rec.confidence == 0.72


def test_human_feedback_creation():
    fb = HumanFeedback(
        action="re_analyze",
        approved_assumptions=["Hiring 5 engineers"],
        rejected_assumptions=["Market size is $3B"],
        removed_options=[],
        updated_constraints={},
        additional_instructions="Dig deeper on market size",
    )
    assert fb.action == "re_analyze"
```

**Step 2: Run test to verify it fails**

Run: `cd /home/david/Documents/projects/multi-agent-chat && python -m pytest backend/tests/test_decision_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'decision'`

**Step 3: Create the package and schemas**

```python
# backend/decision/__init__.py
```

```python
# backend/decision/schemas.py
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class ExpertTask(BaseModel):
    """A task assigned to an expert by the planner."""

    expert_role: str
    deliverable: str


class OptionAnalysis(BaseModel):
    """An expert's analysis of a single decision option."""

    option: str
    claims: list[str]
    numbers: dict[str, Any] = Field(default_factory=dict)
    risks: list[str] = Field(default_factory=list)
    score: float = Field(ge=0, le=10)


class ExpertOutput(BaseModel):
    """Complete output from one expert, covering all options."""

    expert_role: str
    option_analyses: dict[str, OptionAnalysis]
    assumptions: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class Conflict(BaseModel):
    """A detected disagreement between experts."""

    conflict_type: str  # "numeric", "assumption", "risk_assessment"
    topic: str
    experts: list[str]
    values: list[str]


class HumanFeedback(BaseModel):
    """Structured feedback from the human-in-the-loop gate."""

    action: str  # "proceed", "re_analyze", "remove_option"
    approved_assumptions: list[str] = Field(default_factory=list)
    rejected_assumptions: list[str] = Field(default_factory=list)
    removed_options: list[str] = Field(default_factory=list)
    updated_constraints: dict[str, Any] = Field(default_factory=dict)
    additional_instructions: str = ""


class Recommendation(BaseModel):
    """Final structured recommendation from the synthesizer."""

    recommended_option: str
    reasoning: list[str]
    tradeoffs: dict[str, dict]  # option -> {pros: [...], cons: [...]}
    risks: list[str]
    what_would_change_mind: list[str]
    confidence: float = Field(ge=0, le=1)
```

```python
# backend/decision/state.py
from __future__ import annotations

from typing import Annotated, Any, Optional

from typing_extensions import TypedDict

from decision.schemas import (
    Conflict,
    ExpertOutput,
    ExpertTask,
    HumanFeedback,
    Recommendation,
)


def merge_expert_outputs(
    existing: dict[str, ExpertOutput], new: dict[str, ExpertOutput]
) -> dict[str, ExpertOutput]:
    """Reducer: merge expert outputs from parallel Send() calls."""
    merged = {**existing} if existing else {}
    merged.update(new)
    return merged


class DecisionState(TypedDict, total=False):
    # Input
    user_question: str
    constraints: dict[str, Any]

    # Planner output
    decision_options: list[str]
    expert_tasks: list[ExpertTask]

    # Expert outputs (reducer merges parallel results)
    expert_outputs: Annotated[dict[str, ExpertOutput], merge_expert_outputs]

    # Conflict detection
    conflicts: list[Conflict]
    open_questions: list[str]

    # Human-in-the-loop
    human_feedback: Optional[HumanFeedback]

    # Iteration control
    iteration: int
    max_iterations: int

    # Final output
    recommendation: Optional[Recommendation]
    phase: str  # planning | analysis | conflict | human | synthesis | done
```

**Step 4: Run test to verify it passes**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_schemas.py -v`
Expected: All 6 tests PASS

**Step 5: Write state tests**

```python
# Add to backend/tests/test_decision_schemas.py (append)

from decision.state import DecisionState, merge_expert_outputs


def test_merge_expert_outputs_empty():
    result = merge_expert_outputs({}, {"Finance": ExpertOutput(
        expert_role="Finance",
        option_analyses={},
        assumptions=[],
        sources=[],
        confidence=0.5,
    )})
    assert "Finance" in result


def test_merge_expert_outputs_combines():
    existing = {"Finance": ExpertOutput(
        expert_role="Finance",
        option_analyses={},
        assumptions=[],
        sources=[],
        confidence=0.5,
    )}
    new = {"Market": ExpertOutput(
        expert_role="Market",
        option_analyses={},
        assumptions=[],
        sources=[],
        confidence=0.7,
    )}
    result = merge_expert_outputs(existing, new)
    assert "Finance" in result
    assert "Market" in result
    assert len(result) == 2
```

**Step 6: Run all tests**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_schemas.py -v`
Expected: All 8 tests PASS

**Step 7: Commit**

```bash
git add backend/decision/__init__.py backend/decision/schemas.py backend/decision/state.py backend/tests/test_decision_schemas.py
git commit -m "feat(decision): add schemas and state model for decision assistant"
```

---

## Task 2: Planner Node

**Files:**
- Create: `backend/decision/nodes/__init__.py`
- Create: `backend/decision/nodes/planner.py`
- Test: `backend/tests/test_decision_planner.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_decision_planner.py
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decision.nodes.planner import planner_node, PLANNER_SYSTEM_PROMPT


def test_planner_system_prompt_exists():
    assert "decision" in PLANNER_SYSTEM_PROMPT.lower()
    assert "options" in PLANNER_SYSTEM_PROMPT.lower()


@pytest.mark.asyncio
async def test_planner_node_returns_expected_keys():
    """Planner must return decision_options, expert_tasks, and phase."""
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "decision_options": ["Build", "Buy", "Partner"],
        "expert_tasks": [
            {"expert_role": "Finance", "deliverable": "5yr cost model"},
            {"expert_role": "Market", "deliverable": "TAM analysis"},
            {"expert_role": "Risk", "deliverable": "Downside scenarios"},
        ],
    })

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("decision.nodes.planner._get_planner_llm", return_value=mock_llm):
        state = {
            "user_question": "Should we build, buy, or partner for our CRM?",
            "constraints": {"budget": "$2M", "timeline": "6 months"},
        }
        result = await planner_node(state)

    assert "decision_options" in result
    assert "expert_tasks" in result
    assert result["phase"] == "analysis"
    assert len(result["decision_options"]) == 3
    assert len(result["expert_tasks"]) == 3
    assert result["expert_tasks"][0]["expert_role"] == "Finance"
```

**Step 2: Run test to verify it fails**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_planner.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'decision.nodes'`

**Step 3: Implement planner node**

```python
# backend/decision/nodes/__init__.py
```

```python
# backend/decision/nodes/planner.py
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from decision.state import DecisionState
from decision.schemas import ExpertTask

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = """\
You are a Decision Planner. Your job is to decompose a user's decision question \
into concrete options and assign expert analysis tasks.

Given the user's question and constraints, you MUST output valid JSON with exactly \
these fields:

{
  "decision_options": ["Option A", "Option B", ...],
  "expert_tasks": [
    {"expert_role": "RoleName", "deliverable": "What this expert must produce"},
    ...
  ]
}

RULES:
- Identify 2-5 concrete, mutually exclusive decision options
- Assign 2-5 expert roles, each with a specific deliverable
- Expert roles should cover different analytical angles (financial, market, risk, technical, etc.)
- Deliverables must be specific and measurable, not vague
- Do NOT include any text outside the JSON object
"""


def _get_planner_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0.2,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


async def planner_node(state: DecisionState) -> dict[str, Any]:
    """Decompose the user's question into options and expert tasks."""
    llm = _get_planner_llm()

    user_content = f"Question: {state['user_question']}"
    if state.get("constraints"):
        user_content += f"\nConstraints: {json.dumps(state['constraints'])}"

    messages = [
        SystemMessage(content=PLANNER_SYSTEM_PROMPT),
        HumanMessage(content=user_content),
    ]

    response = await llm.ainvoke(messages)
    parsed = json.loads(response.content)

    expert_tasks = [
        ExpertTask(**task) if isinstance(task, dict) else task
        for task in parsed["expert_tasks"]
    ]

    logger.info(
        "Planner identified %d options and %d expert tasks",
        len(parsed["decision_options"]),
        len(expert_tasks),
    )

    return {
        "decision_options": parsed["decision_options"],
        "expert_tasks": [t.model_dump() if isinstance(t, ExpertTask) else t for t in expert_tasks],
        "phase": "analysis",
    }
```

**Step 4: Run test to verify it passes**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_planner.py -v`
Expected: All 2 tests PASS

**Step 5: Commit**

```bash
git add backend/decision/nodes/__init__.py backend/decision/nodes/planner.py backend/tests/test_decision_planner.py
git commit -m "feat(decision): add planner node - decomposes question into options and expert tasks"
```

---

## Task 3: Expert Tools (Search + Calculator)

**Files:**
- Create: `backend/decision/tools/__init__.py`
- Create: `backend/decision/tools/search.py`
- Create: `backend/decision/tools/calculator.py`
- Test: `backend/tests/test_decision_tools.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_decision_tools.py
import pytest
from unittest.mock import patch, MagicMock
from decision.tools.search import create_search_tool
from decision.tools.calculator import create_calculator_tool


def test_search_tool_has_correct_name():
    tool = create_search_tool()
    assert tool.name == "web_search"


def test_calculator_tool_has_correct_name():
    tool = create_calculator_tool()
    assert tool.name == "calculator"


def test_calculator_tool_evaluates_expression():
    tool = create_calculator_tool()
    result = tool.invoke({"expression": "2 + 2"})
    assert "4" in str(result)


def test_calculator_tool_handles_complex_expression():
    tool = create_calculator_tool()
    result = tool.invoke({"expression": "500000 * 1.05 ** 5"})
    assert "638140" in str(result)


def test_calculator_tool_rejects_dangerous_code():
    tool = create_calculator_tool()
    result = tool.invoke({"expression": "__import__('os').system('ls')"})
    assert "error" in str(result).lower() or "not allowed" in str(result).lower()
```

**Step 2: Run test to verify it fails**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_tools.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement tools**

```python
# backend/decision/tools/__init__.py
```

```python
# backend/decision/tools/search.py
from __future__ import annotations

import os
from langchain_core.tools import tool


def create_search_tool():
    """Create a Tavily web search tool for expert agents."""

    @tool
    def web_search(query: str) -> str:
        """Search the web for current information. Returns relevant results as text."""
        from tavily import TavilyClient

        api_key = os.environ.get("TAVILY_API_KEY", "")
        if not api_key:
            return "Error: TAVILY_API_KEY not set"

        client = TavilyClient(api_key=api_key)
        results = client.search(query, max_results=5, search_depth="advanced")

        formatted = []
        for r in results.get("results", []):
            formatted.append(
                f"Title: {r.get('title', 'N/A')}\n"
                f"URL: {r.get('url', 'N/A')}\n"
                f"Content: {r.get('content', 'N/A')}\n"
            )
        return "\n---\n".join(formatted) if formatted else "No results found."

    return web_search
```

```python
# backend/decision/tools/calculator.py
from __future__ import annotations

import ast
import math
import operator
from langchain_core.tools import tool

# Safe operations whitelist
_SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_FUNCTIONS = {
    "abs": abs,
    "round": round,
    "min": min,
    "max": max,
    "sum": sum,
    "int": int,
    "float": float,
    "sqrt": math.sqrt,
    "log": math.log,
    "log10": math.log10,
    "ceil": math.ceil,
    "floor": math.floor,
}


def _safe_eval(expr: str) -> float | int:
    """Evaluate a math expression safely using AST parsing."""
    tree = ast.parse(expr, mode="eval")

    def _eval_node(node):
        if isinstance(node, ast.Expression):
            return _eval_node(node.body)
        elif isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)):
                return node.value
            raise ValueError(f"Constant type not allowed: {type(node.value)}")
        elif isinstance(node, ast.BinOp):
            op_type = type(node.op)
            if op_type not in _SAFE_OPERATORS:
                raise ValueError(f"Operator not allowed: {op_type.__name__}")
            left = _eval_node(node.left)
            right = _eval_node(node.right)
            return _SAFE_OPERATORS[op_type](left, right)
        elif isinstance(node, ast.UnaryOp):
            op_type = type(node.op)
            if op_type not in _SAFE_OPERATORS:
                raise ValueError(f"Operator not allowed: {op_type.__name__}")
            return _SAFE_OPERATORS[op_type](_eval_node(node.operand))
        elif isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name):
                raise ValueError("Only simple function calls allowed")
            func_name = node.func.id
            if func_name not in _SAFE_FUNCTIONS:
                raise ValueError(f"Function not allowed: {func_name}")
            args = [_eval_node(arg) for arg in node.args]
            return _SAFE_FUNCTIONS[func_name](*args)
        elif isinstance(node, ast.List):
            return [_eval_node(el) for el in node.elts]
        elif isinstance(node, ast.Tuple):
            return tuple(_eval_node(el) for el in node.elts)
        else:
            raise ValueError(f"Expression type not allowed: {type(node).__name__}")

    return _eval_node(tree)


def create_calculator_tool():
    """Create a safe calculator tool for expert agents."""

    @tool
    def calculator(expression: str) -> str:
        """Evaluate a mathematical expression. Supports basic arithmetic, exponents,
        and functions: abs, round, min, max, sum, sqrt, log, log10, ceil, floor.
        Example: '500000 * 1.05 ** 5' or 'sqrt(144) + round(3.7)'"""
        try:
            result = _safe_eval(expression)
            return f"{expression} = {result}"
        except Exception as e:
            return f"Error: {e}. Expression not allowed or invalid."

    return calculator
```

**Step 4: Run test to verify it passes**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_tools.py -v`
Expected: All 5 tests PASS

**Step 5: Commit**

```bash
git add backend/decision/tools/__init__.py backend/decision/tools/search.py backend/decision/tools/calculator.py backend/tests/test_decision_tools.py
git commit -m "feat(decision): add search and calculator tools for expert agents"
```

---

## Task 4: Expert Node (with tools + parallel Send)

**Files:**
- Create: `backend/decision/nodes/expert.py`
- Test: `backend/tests/test_decision_expert.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_decision_expert.py
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decision.nodes.expert import run_expert, fan_out_experts, EXPERT_SYSTEM_PROMPT
from decision.schemas import ExpertTask


def test_expert_system_prompt_enforces_commitment():
    prompt = EXPERT_SYSTEM_PROMPT
    assert "commit" in prompt.lower() or "specific" in prompt.lower()
    assert "hedge" in prompt.lower() or "it depends" in prompt.lower()


def test_fan_out_experts_returns_send_objects():
    state = {
        "expert_tasks": [
            {"expert_role": "Finance", "deliverable": "Cost model"},
            {"expert_role": "Market", "deliverable": "TAM analysis"},
        ],
        "decision_options": ["Build", "Buy"],
        "constraints": {"budget": "$2M"},
    }
    sends = fan_out_experts(state)
    assert len(sends) == 2
    # Each Send should target "run_expert" node
    for s in sends:
        assert s.node == "run_expert"


@pytest.mark.asyncio
async def test_run_expert_returns_expert_output():
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "expert_role": "Finance",
        "option_analyses": {
            "Build": {
                "option": "Build",
                "claims": ["Lower long-term cost"],
                "numbers": {"year_1": 500000},
                "risks": ["Hiring risk"],
                "score": 7.0,
            },
            "Buy": {
                "option": "Buy",
                "claims": ["Faster deployment"],
                "numbers": {"year_1": 300000},
                "risks": ["Vendor lock-in"],
                "score": 6.5,
            },
        },
        "assumptions": ["5 engineers needed"],
        "sources": [],
        "confidence": 0.75,
    })

    # Simulate a tool-calling agent that returns final response
    mock_llm_instance = AsyncMock()
    mock_llm_instance.ainvoke = AsyncMock(return_value=mock_response)
    mock_llm_instance.bind_tools = MagicMock(return_value=mock_llm_instance)

    with patch("decision.nodes.expert._get_expert_llm", return_value=mock_llm_instance):
        state = {
            "expert_task": {"expert_role": "Finance", "deliverable": "Cost model"},
            "decision_options": ["Build", "Buy"],
            "constraints": {"budget": "$2M"},
        }
        result = await run_expert(state)

    assert "expert_outputs" in result
    assert "Finance" in result["expert_outputs"]
    output = result["expert_outputs"]["Finance"]
    assert output["confidence"] == 0.75
```

**Step 2: Run test to verify it fails**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_expert.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement expert node**

```python
# backend/decision/nodes/expert.py
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Send

from decision.schemas import ExpertOutput, ExpertTask
from decision.tools.search import create_search_tool
from decision.tools.calculator import create_calculator_tool

logger = logging.getLogger(__name__)

EXPERT_SYSTEM_PROMPT = """\
You are a {role} Expert analyzing a decision.

The user must choose between these options: {options}
Constraints: {constraints}

YOUR DELIVERABLE: {deliverable}

You have access to tools:
- web_search: Search the web for current data, market info, pricing, etc.
- calculator: Evaluate math expressions for financial projections, comparisons.

OUTPUT FORMAT: You MUST return valid JSON matching this exact schema:
{{
  "expert_role": "{role}",
  "option_analyses": {{
    "<option_name>": {{
      "option": "<option_name>",
      "claims": ["specific claim 1", "specific claim 2"],
      "numbers": {{"metric_name": value}},
      "risks": ["specific risk 1"],
      "score": <0-10 rating>
    }}
  }},
  "assumptions": ["assumption 1", "assumption 2"],
  "sources": ["url or reference"],
  "confidence": <0.0-1.0>
}}

RULES:
- Analyze EACH option separately with specific claims and numbers
- Commit to specific numbers, not ranges — if uncertain, state your best estimate
- State ALL assumptions explicitly — hidden assumptions are failures
- Rate each option 0-10 with justification in claims
- If you use web_search, cite the source URL
- Do NOT hedge with "it depends" — commit to a position given the constraints
- Do NOT include any text outside the JSON object
"""


def _get_expert_llm() -> ChatOpenAI:
    return ChatOpenAI(model="gpt-4o", temperature=0.3)


def fan_out_experts(state: dict[str, Any]) -> list[Send]:
    """Fan out expert tasks to parallel run_expert nodes via Send()."""
    sends = []
    for task in state["expert_tasks"]:
        task_data = task if isinstance(task, dict) else task.model_dump()
        sends.append(
            Send(
                "run_expert",
                {
                    "expert_task": task_data,
                    "decision_options": state["decision_options"],
                    "constraints": state.get("constraints", {}),
                },
            )
        )
    return sends


async def run_expert(state: dict[str, Any]) -> dict[str, Any]:
    """Run a single expert analysis. Called in parallel via Send()."""
    task = state["expert_task"]
    if isinstance(task, dict):
        task = ExpertTask(**task)

    options_str = ", ".join(state.get("decision_options", []))
    constraints_str = json.dumps(state.get("constraints", {}))

    system_prompt = EXPERT_SYSTEM_PROMPT.format(
        role=task.expert_role,
        options=options_str,
        constraints=constraints_str,
        deliverable=task.deliverable,
    )

    llm = _get_expert_llm()
    tools = [create_search_tool(), create_calculator_tool()]
    llm_with_tools = llm.bind_tools(tools)

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=f"Analyze the decision options and produce your {task.deliverable}. "
            f"Use tools if you need current data or calculations. "
            f"Return ONLY the JSON output."
        ),
    ]

    # Agent loop: handle tool calls until we get a final response
    max_tool_rounds = 5
    for _ in range(max_tool_rounds):
        response = await llm_with_tools.ainvoke(messages)
        messages.append(response)

        if not response.tool_calls:
            break

        # Execute tool calls and add results
        for tool_call in response.tool_calls:
            tool_fn = next(
                (t for t in tools if t.name == tool_call["name"]), None
            )
            if tool_fn:
                tool_result = tool_fn.invoke(tool_call["args"])
                from langchain_core.messages import ToolMessage

                messages.append(
                    ToolMessage(content=str(tool_result), tool_call_id=tool_call["id"])
                )

    # Parse the final response
    try:
        parsed = json.loads(response.content)
        output = ExpertOutput(**parsed)
    except (json.JSONDecodeError, Exception) as e:
        logger.error("Expert %s failed to produce valid JSON: %s", task.expert_role, e)
        # Return a minimal error output
        output = ExpertOutput(
            expert_role=task.expert_role,
            option_analyses={},
            assumptions=[f"Error: {e}"],
            sources=[],
            confidence=0.0,
        )

    return {"expert_outputs": {task.expert_role: output.model_dump()}}
```

**Step 4: Run test to verify it passes**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_expert.py -v`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add backend/decision/nodes/expert.py backend/tests/test_decision_expert.py
git commit -m "feat(decision): add expert node with tool-calling agent loop and Send() fan-out"
```

---

## Task 5: Conflict Detector Node

**Files:**
- Create: `backend/decision/nodes/conflict_detector.py`
- Test: `backend/tests/test_decision_conflict.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_decision_conflict.py
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decision.nodes.conflict_detector import conflict_detector_node


@pytest.mark.asyncio
async def test_conflict_detector_finds_numeric_conflict():
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "conflicts": [
            {
                "conflict_type": "numeric",
                "topic": "Year 1 cost for Build option",
                "experts": ["Finance", "Market"],
                "values": ["$500K", "$800K"],
            }
        ],
        "open_questions": ["Are infrastructure costs included?"],
    })

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("decision.nodes.conflict_detector._get_detector_llm", return_value=mock_llm):
        state = {
            "expert_outputs": {
                "Finance": {
                    "expert_role": "Finance",
                    "option_analyses": {
                        "Build": {"option": "Build", "claims": [], "numbers": {"year_1": 500000}, "risks": [], "score": 7.0}
                    },
                    "assumptions": ["5 engineers"],
                    "sources": [],
                    "confidence": 0.8,
                },
                "Market": {
                    "expert_role": "Market",
                    "option_analyses": {
                        "Build": {"option": "Build", "claims": [], "numbers": {"year_1": 800000}, "risks": [], "score": 5.0}
                    },
                    "assumptions": ["10 engineers"],
                    "sources": [],
                    "confidence": 0.7,
                },
            },
            "decision_options": ["Build", "Buy"],
        }
        result = await conflict_detector_node(state)

    assert "conflicts" in result
    assert "open_questions" in result
    assert result["phase"] == "conflict"
    assert len(result["conflicts"]) >= 1


@pytest.mark.asyncio
async def test_conflict_detector_no_conflicts():
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "conflicts": [],
        "open_questions": [],
    })

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("decision.nodes.conflict_detector._get_detector_llm", return_value=mock_llm):
        state = {
            "expert_outputs": {"Finance": {"expert_role": "Finance", "option_analyses": {}, "assumptions": [], "sources": [], "confidence": 0.8}},
            "decision_options": ["Build"],
        }
        result = await conflict_detector_node(state)

    assert result["conflicts"] == []
    assert result["phase"] == "conflict"
```

**Step 2: Run test to verify it fails**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_conflict.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement conflict detector**

```python
# backend/decision/nodes/conflict_detector.py
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from decision.state import DecisionState

logger = logging.getLogger(__name__)

DETECTOR_SYSTEM_PROMPT = """\
You are a Conflict Detector. Your job is to find disagreements and gaps \
between expert analyses of a decision.

You will receive structured outputs from multiple experts, each analyzing \
the same set of decision options.

OUTPUT FORMAT: Return valid JSON:
{{
  "conflicts": [
    {{
      "conflict_type": "numeric" | "assumption" | "risk_assessment",
      "topic": "what the disagreement is about",
      "experts": ["Expert1", "Expert2"],
      "values": ["Expert1's value/position", "Expert2's value/position"]
    }}
  ],
  "open_questions": [
    "Unresolved question that no expert addressed"
  ]
}}

DETECTION RULES:
- NUMERIC: Flag when two experts' numbers for the same metric differ by >20%
- ASSUMPTION: Flag when experts assume contradictory things
- RISK_ASSESSMENT: Flag when experts rate the same risk very differently
- GAPS: Note questions that no expert addressed
- Do NOT resolve conflicts — only surface them
- Do NOT include any text outside the JSON object
- If no conflicts exist, return empty lists
"""


def _get_detector_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0.1,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


async def conflict_detector_node(state: DecisionState) -> dict[str, Any]:
    """Detect conflicts and gaps between expert outputs."""
    llm = _get_detector_llm()

    expert_summary = json.dumps(state.get("expert_outputs", {}), indent=2, default=str)

    messages = [
        SystemMessage(content=DETECTOR_SYSTEM_PROMPT),
        HumanMessage(
            content=f"Decision options: {state.get('decision_options', [])}\n\n"
            f"Expert outputs:\n{expert_summary}\n\n"
            f"Find all conflicts, assumption mismatches, and unanswered questions."
        ),
    ]

    response = await llm.ainvoke(messages)
    parsed = json.loads(response.content)

    conflicts = parsed.get("conflicts", [])
    open_questions = parsed.get("open_questions", [])

    logger.info("Detected %d conflicts and %d open questions", len(conflicts), len(open_questions))

    return {
        "conflicts": conflicts,
        "open_questions": open_questions,
        "phase": "conflict",
    }
```

**Step 4: Run test to verify it passes**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_conflict.py -v`
Expected: All 2 tests PASS

**Step 5: Commit**

```bash
git add backend/decision/nodes/conflict_detector.py backend/tests/test_decision_conflict.py
git commit -m "feat(decision): add conflict detector node - surfaces expert disagreements"
```

---

## Task 6: Human Gate Node

**Files:**
- Create: `backend/decision/nodes/human_gate.py`
- Test: `backend/tests/test_decision_human_gate.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_decision_human_gate.py
import pytest
from decision.nodes.human_gate import human_gate_node, route_after_human


def test_route_after_human_proceed():
    state = {
        "human_feedback": {"action": "proceed"},
        "iteration": 0,
        "max_iterations": 2,
    }
    assert route_after_human(state) == "synthesizer"


def test_route_after_human_re_analyze():
    state = {
        "human_feedback": {"action": "re_analyze"},
        "iteration": 0,
        "max_iterations": 2,
    }
    assert route_after_human(state) == "fan_out_experts"


def test_route_after_human_re_analyze_at_max():
    state = {
        "human_feedback": {"action": "re_analyze"},
        "iteration": 2,
        "max_iterations": 2,
    }
    assert route_after_human(state) == "synthesizer"


def test_route_after_human_no_feedback():
    state = {
        "human_feedback": None,
        "iteration": 0,
        "max_iterations": 2,
    }
    assert route_after_human(state) == "synthesizer"
```

**Step 2: Run test to verify it fails**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_human_gate.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement human gate**

```python
# backend/decision/nodes/human_gate.py
from __future__ import annotations

import logging
from typing import Any

from langgraph.types import interrupt

from decision.state import DecisionState

logger = logging.getLogger(__name__)


async def human_gate_node(state: DecisionState) -> dict[str, Any]:
    """Pause execution and wait for human feedback on conflicts."""
    interrupt_value = {
        "decision_options": state.get("decision_options", []),
        "expert_outputs": state.get("expert_outputs", {}),
        "conflicts": state.get("conflicts", []),
        "open_questions": state.get("open_questions", []),
    }

    # This pauses the graph until Command(resume=...) is called
    human_input = interrupt(value=interrupt_value)

    logger.info("Human feedback received: %s", human_input.get("action") if isinstance(human_input, dict) else human_input)

    iteration = state.get("iteration", 0) + 1

    return {
        "human_feedback": human_input if isinstance(human_input, dict) else {"action": "proceed"},
        "iteration": iteration,
        "phase": "human",
    }


def route_after_human(state: DecisionState) -> str:
    """Route after human gate: re-analyze or proceed to synthesis."""
    feedback = state.get("human_feedback")
    if not feedback:
        return "synthesizer"

    action = feedback.get("action", "proceed") if isinstance(feedback, dict) else "proceed"
    iteration = state.get("iteration", 0)
    max_iterations = state.get("max_iterations", 2)

    if action == "re_analyze" and iteration < max_iterations:
        return "fan_out_experts"

    return "synthesizer"
```

**Step 4: Run test to verify it passes**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_human_gate.py -v`
Expected: All 4 tests PASS

**Step 5: Commit**

```bash
git add backend/decision/nodes/human_gate.py backend/tests/test_decision_human_gate.py
git commit -m "feat(decision): add human gate node with interrupt() and routing logic"
```

---

## Task 7: Synthesizer Node

**Files:**
- Create: `backend/decision/nodes/synthesizer.py`
- Test: `backend/tests/test_decision_synthesizer.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_decision_synthesizer.py
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decision.nodes.synthesizer import synthesizer_node, SYNTHESIZER_SYSTEM_PROMPT


def test_synthesizer_prompt_is_not_a_summarizer():
    prompt = SYNTHESIZER_SYSTEM_PROMPT
    assert "compare" in prompt.lower() or "tradeoff" in prompt.lower()
    assert "summariz" not in prompt.lower()


@pytest.mark.asyncio
async def test_synthesizer_returns_recommendation():
    mock_response = MagicMock()
    mock_response.content = json.dumps({
        "recommended_option": "Buy",
        "reasoning": ["Faster time to market", "Lower initial risk"],
        "tradeoffs": {
            "Build": {"pros": ["Full control"], "cons": ["Slow", "Expensive"]},
            "Buy": {"pros": ["Fast", "Proven"], "cons": ["Vendor lock-in"]},
        },
        "risks": ["Vendor may raise prices"],
        "what_would_change_mind": ["If build timeline < 3 months"],
        "confidence": 0.72,
    })

    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=mock_response)

    with patch("decision.nodes.synthesizer._get_synthesizer_llm", return_value=mock_llm):
        state = {
            "user_question": "Build or buy CRM?",
            "constraints": {"budget": "$2M"},
            "decision_options": ["Build", "Buy"],
            "expert_outputs": {
                "Finance": {
                    "expert_role": "Finance",
                    "option_analyses": {},
                    "assumptions": [],
                    "sources": [],
                    "confidence": 0.8,
                },
            },
            "conflicts": [],
            "open_questions": [],
            "human_feedback": None,
        }
        result = await synthesizer_node(state)

    assert "recommendation" in result
    assert result["phase"] == "done"
    rec = result["recommendation"]
    assert rec["recommended_option"] == "Buy"
    assert rec["confidence"] == 0.72
    assert len(rec["reasoning"]) > 0
```

**Step 2: Run test to verify it fails**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_synthesizer.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement synthesizer**

```python
# backend/decision/nodes/synthesizer.py
from __future__ import annotations

import json
import logging
from typing import Any

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from decision.state import DecisionState
from decision.schemas import Recommendation

logger = logging.getLogger(__name__)

SYNTHESIZER_SYSTEM_PROMPT = """\
You are a Decision Synthesizer. You compare options head-to-head using \
expert analysis data and produce a structured recommendation.

You are NOT a summarizer. Do NOT restate what experts said. Instead:
- Compare options directly on each dimension
- Identify the key tradeoff that drives the recommendation
- Be explicit about what risks remain
- State what evidence would change your recommendation

OUTPUT FORMAT: Return valid JSON:
{{
  "recommended_option": "Option Name",
  "reasoning": ["Key reason 1", "Key reason 2"],
  "tradeoffs": {{
    "Option A": {{"pros": ["..."], "cons": ["..."]}},
    "Option B": {{"pros": ["..."], "cons": ["..."]}}
  }},
  "risks": ["Remaining risk 1", "Remaining risk 2"],
  "what_would_change_mind": ["If X were true, I would recommend Y instead"],
  "confidence": 0.0-1.0
}}

RULES:
- Every option MUST appear in tradeoffs with both pros AND cons
- Reasoning must reference specific expert data, not generic statements
- "what_would_change_mind" must be falsifiable conditions, not vague
- Confidence reflects certainty: 0.5 = coin flip, 0.8+ = strong conviction
- Do NOT include any text outside the JSON object
"""


def _get_synthesizer_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model="gpt-4o",
        temperature=0.2,
        model_kwargs={"response_format": {"type": "json_object"}},
    )


async def synthesizer_node(state: DecisionState) -> dict[str, Any]:
    """Produce a structured recommendation by comparing options head-to-head."""
    llm = _get_synthesizer_llm()

    expert_data = json.dumps(state.get("expert_outputs", {}), indent=2, default=str)
    conflicts_data = json.dumps(state.get("conflicts", []), indent=2, default=str)
    human_feedback = state.get("human_feedback")
    feedback_str = json.dumps(human_feedback, indent=2, default=str) if human_feedback else "None"

    messages = [
        SystemMessage(content=SYNTHESIZER_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Original question: {state.get('user_question', '')}\n"
                f"Constraints: {json.dumps(state.get('constraints', {}))}\n"
                f"Options: {state.get('decision_options', [])}\n\n"
                f"Expert analyses:\n{expert_data}\n\n"
                f"Detected conflicts:\n{conflicts_data}\n\n"
                f"Open questions: {state.get('open_questions', [])}\n\n"
                f"Human feedback: {feedback_str}\n\n"
                f"Compare the options head-to-head and produce your recommendation."
            )
        ),
    ]

    response = await llm.ainvoke(messages)
    parsed = json.loads(response.content)
    recommendation = Recommendation(**parsed)

    logger.info(
        "Synthesizer recommends: %s (confidence: %.2f)",
        recommendation.recommended_option,
        recommendation.confidence,
    )

    return {
        "recommendation": recommendation.model_dump(),
        "phase": "done",
    }
```

**Step 4: Run test to verify it passes**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_synthesizer.py -v`
Expected: All 2 tests PASS

**Step 5: Commit**

```bash
git add backend/decision/nodes/synthesizer.py backend/tests/test_decision_synthesizer.py
git commit -m "feat(decision): add synthesizer node - head-to-head option comparison"
```

---

## Task 8: LangGraph StateGraph Assembly

**Files:**
- Create: `backend/decision/graph.py`
- Test: `backend/tests/test_decision_graph.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_decision_graph.py
import pytest
from decision.graph import build_decision_graph


def test_graph_compiles():
    graph = build_decision_graph()
    assert graph is not None


def test_graph_has_expected_nodes():
    graph = build_decision_graph()
    # LangGraph compiled graph exposes nodes
    node_names = set(graph.nodes.keys())
    expected = {"planner", "run_expert", "conflict_detector", "human_gate", "synthesizer"}
    assert expected.issubset(node_names), f"Missing nodes: {expected - node_names}"


def test_graph_has_start_edge():
    graph = build_decision_graph()
    # The graph should have an edge from __start__ to planner
    # We verify by checking the graph structure
    assert "planner" in graph.nodes
```

**Step 2: Run test to verify it fails**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_graph.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Implement the graph**

```python
# backend/decision/graph.py
from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import InMemorySaver

from decision.state import DecisionState
from decision.nodes.planner import planner_node
from decision.nodes.expert import run_expert, fan_out_experts
from decision.nodes.conflict_detector import conflict_detector_node
from decision.nodes.human_gate import human_gate_node, route_after_human
from decision.nodes.synthesizer import synthesizer_node

logger = logging.getLogger(__name__)


def _route_after_conflicts(state: DecisionState) -> str:
    """Route after conflict detection: human gate if conflicts, else synthesize."""
    conflicts = state.get("conflicts", [])
    if conflicts:
        return "human_gate"
    return "synthesizer"


def build_decision_graph(checkpointer=None):
    """Build and compile the decision assistant LangGraph."""
    builder = StateGraph(DecisionState)

    # Add nodes
    builder.add_node("planner", planner_node)
    builder.add_node("run_expert", run_expert)
    builder.add_node("conflict_detector", conflict_detector_node)
    builder.add_node("human_gate", human_gate_node)
    builder.add_node("synthesizer", synthesizer_node)

    # Edges
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

    # Human gate -> conditional: re-analyze or synthesize
    builder.add_conditional_edges(
        "human_gate",
        route_after_human,
        {"fan_out_experts": "planner", "synthesizer": "synthesizer"},
    )

    # Synthesizer -> END
    builder.add_edge("synthesizer", END)

    # Compile with checkpointer (required for interrupt())
    if checkpointer is None:
        checkpointer = InMemorySaver()

    return builder.compile(checkpointer=checkpointer)
```

**Step 4: Run test to verify it passes**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_graph.py -v`
Expected: All 3 tests PASS

**Step 5: Commit**

```bash
git add backend/decision/graph.py backend/tests/test_decision_graph.py
git commit -m "feat(decision): assemble LangGraph StateGraph with Send() fan-out and interrupt()"
```

---

## Task 9: SSE Streaming Endpoint

**Files:**
- Modify: `backend/main.py` — Add `/decision-stream` endpoint
- Test: `backend/tests/test_decision_endpoint.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_decision_endpoint.py
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient


def test_decision_stream_endpoint_exists():
    """The /decision-stream endpoint should exist and accept POST."""
    # Import after patching to avoid requiring real env vars
    with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}):
        from main import app
        client = TestClient(app)
        # Should not 404 — it should fail for other reasons (no real LLM)
        response = client.post(
            "/decision-stream",
            json={
                "thread_id": "test-thread",
                "question": "Should we build or buy?",
                "constraints": {"budget": "$1M"},
            },
        )
        # We expect 200 with SSE content type (even if stream errors)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
```

**Step 2: Run test to verify it fails**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_endpoint.py -v`
Expected: FAIL with 404 or missing endpoint

**Step 3: Add the endpoint to main.py**

Add the following to `backend/main.py`. Find the existing imports section and add:

```python
# Near top of main.py, with other imports
from decision.graph import build_decision_graph
```

Add a new Pydantic model for the request (near existing AskRequest):

```python
class DecisionRequest(BaseModel):
    thread_id: str
    question: str
    constraints: dict | None = None
    max_iterations: int = 2
    resume: bool = False
    human_feedback: dict | None = None
```

Add the endpoint (after existing routes, before static file serving):

```python
@app.post("/decision-stream")
async def decision_stream(req: DecisionRequest, request: Request):
    """Stream a decision assistant session via SSE."""
    import uuid

    async def event_generator():
        try:
            graph = build_decision_graph()
            config = {"configurable": {"thread_id": req.thread_id}}

            if req.resume and req.human_feedback:
                # Resume after human gate interrupt
                from langgraph.types import Command
                stream = graph.astream(
                    Command(resume=req.human_feedback),
                    config,
                    stream_mode="updates",
                )
            else:
                # Start new decision
                initial_state = {
                    "user_question": req.question,
                    "constraints": req.constraints or {},
                    "iteration": 0,
                    "max_iterations": req.max_iterations,
                    "phase": "planning",
                    "expert_outputs": {},
                }
                stream = graph.astream(
                    initial_state,
                    config,
                    stream_mode="updates",
                )

            async for event in stream:
                for node_name, node_output in event.items():
                    if node_name == "__interrupt__":
                        # Human gate triggered
                        yield f"data: {json.dumps({'type': 'awaiting_input', 'data': node_output})}\n\n"
                        continue

                    phase = node_output.get("phase", "")

                    if node_name == "planner":
                        yield f"data: {json.dumps({'type': 'phase_update', 'phase': 'planning'})}\n\n"
                        yield f"data: {json.dumps({'type': 'options_identified', 'options': node_output.get('decision_options', []), 'expert_tasks': node_output.get('expert_tasks', [])})}\n\n"

                    elif node_name == "run_expert":
                        outputs = node_output.get("expert_outputs", {})
                        for role, output in outputs.items():
                            yield f"data: {json.dumps({'type': 'expert_complete', 'expert_role': role, 'output': output})}\n\n"

                    elif node_name == "conflict_detector":
                        yield f"data: {json.dumps({'type': 'phase_update', 'phase': 'conflict'})}\n\n"
                        yield f"data: {json.dumps({'type': 'conflicts_detected', 'conflicts': node_output.get('conflicts', []), 'open_questions': node_output.get('open_questions', [])})}\n\n"

                    elif node_name == "human_gate":
                        yield f"data: {json.dumps({'type': 'phase_update', 'phase': 'human'})}\n\n"

                    elif node_name == "synthesizer":
                        yield f"data: {json.dumps({'type': 'phase_update', 'phase': 'synthesis'})}\n\n"
                        yield f"data: {json.dumps({'type': 'recommendation', 'recommendation': node_output.get('recommendation', {})})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.error("Decision stream error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

**Step 4: Run test to verify it passes**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_endpoint.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/main.py backend/tests/test_decision_endpoint.py
git commit -m "feat(decision): add /decision-stream SSE endpoint to FastAPI"
```

---

## Task 10: Frontend Types and API

**Files:**
- Modify: `frontend/src/types.ts` — Add decision types
- Modify: `frontend/src/api.ts` — Add `decisionStream()` function

**Step 1: Add TypeScript types**

Add to `frontend/src/types.ts`:

```typescript
// Decision Assistant types
export interface ExpertTask {
  expert_role: string;
  deliverable: string;
}

export interface OptionAnalysis {
  option: string;
  claims: string[];
  numbers: Record<string, number | string>;
  risks: string[];
  score: number;
}

export interface ExpertOutput {
  expert_role: string;
  option_analyses: Record<string, OptionAnalysis>;
  assumptions: string[];
  sources: string[];
  confidence: number;
}

export interface Conflict {
  conflict_type: string;
  topic: string;
  experts: string[];
  values: string[];
}

export interface Recommendation {
  recommended_option: string;
  reasoning: string[];
  tradeoffs: Record<string, { pros: string[]; cons: string[] }>;
  risks: string[];
  what_would_change_mind: string[];
  confidence: number;
}

export interface HumanFeedback {
  action: "proceed" | "re_analyze" | "remove_option";
  approved_assumptions?: string[];
  rejected_assumptions?: string[];
  removed_options?: string[];
  updated_constraints?: Record<string, unknown>;
  additional_instructions?: string;
}

export interface DecisionRequestBody {
  thread_id: string;
  question: string;
  constraints?: Record<string, unknown>;
  max_iterations?: number;
  resume?: boolean;
  human_feedback?: HumanFeedback;
}

export type DecisionPhase = "planning" | "analysis" | "conflict" | "human" | "synthesis" | "done";
```

**Step 2: Add SSE streaming function to api.ts**

Add to `frontend/src/api.ts`:

```typescript
export async function decisionStream(
  body: DecisionRequestBody,
  callbacks: {
    onPhaseUpdate?: (phase: DecisionPhase) => void;
    onOptionsIdentified?: (options: string[], expertTasks: ExpertTask[]) => void;
    onExpertComplete?: (expertRole: string, output: ExpertOutput) => void;
    onConflictsDetected?: (conflicts: Conflict[], openQuestions: string[]) => void;
    onAwaitingInput?: (data: unknown) => void;
    onRecommendation?: (recommendation: Recommendation) => void;
    onError?: (error: Error) => void;
  },
  signal?: AbortSignal
): Promise<void> {
  const apiBase = import.meta.env.VITE_API_URL || "";
  const response = await fetch(`${apiBase}/decision-stream`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    throw new Error(`Decision stream failed: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        try {
          const event = JSON.parse(line.slice(6));

          switch (event.type) {
            case "phase_update":
              callbacks.onPhaseUpdate?.(event.phase);
              break;
            case "options_identified":
              callbacks.onOptionsIdentified?.(event.options, event.expert_tasks);
              break;
            case "expert_complete":
              callbacks.onExpertComplete?.(event.expert_role, event.output);
              break;
            case "conflicts_detected":
              callbacks.onConflictsDetected?.(event.conflicts, event.open_questions);
              break;
            case "awaiting_input":
              callbacks.onAwaitingInput?.(event.data);
              break;
            case "recommendation":
              callbacks.onRecommendation?.(event.recommendation);
              break;
            case "error":
              callbacks.onError?.(new Error(event.message));
              break;
            case "done":
              return;
          }
        } catch (e) {
          console.warn("Failed to parse SSE event:", line, e);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
```

**Step 3: Commit**

```bash
git add frontend/src/types.ts frontend/src/api.ts
git commit -m "feat(frontend): add decision assistant types and SSE streaming API"
```

---

## Task 11: DecisionViewer Component

**Files:**
- Create: `frontend/src/components/DecisionViewer.tsx`

**Step 1: Create the phase-driven viewer**

```tsx
// frontend/src/components/DecisionViewer.tsx
import React from "react";
import type {
  DecisionPhase,
  ExpertTask,
  ExpertOutput,
  Conflict,
  Recommendation,
} from "../types";
import { ExpertCard } from "./ExpertCard";
import { ConflictPanel } from "./ConflictPanel";
import { RecommendationPanel } from "./RecommendationPanel";

interface DecisionViewerProps {
  phase: DecisionPhase;
  options: string[];
  expertTasks: ExpertTask[];
  expertOutputs: Record<string, ExpertOutput>;
  conflicts: Conflict[];
  openQuestions: string[];
  recommendation: Recommendation | null;
  awaitingInput: boolean;
  onHumanFeedback?: (feedback: { action: string; additional_instructions?: string }) => void;
}

const PHASE_STEPS: { key: DecisionPhase; label: string }[] = [
  { key: "planning", label: "Planning" },
  { key: "analysis", label: "Analysis" },
  { key: "conflict", label: "Conflicts" },
  { key: "synthesis", label: "Decision" },
];

function phaseDone(current: DecisionPhase, step: DecisionPhase): boolean {
  const order = PHASE_STEPS.map((s) => s.key);
  return order.indexOf(current) > order.indexOf(step);
}

function phaseActive(current: DecisionPhase, step: DecisionPhase): boolean {
  return current === step || (step === "conflict" && current === "human");
}

export function DecisionViewer({
  phase,
  options,
  expertTasks,
  expertOutputs,
  conflicts,
  openQuestions,
  recommendation,
  awaitingInput,
  onHumanFeedback,
}: DecisionViewerProps) {
  const [feedbackText, setFeedbackText] = React.useState("");

  return (
    <div className="space-y-4">
      {/* Phase stepper */}
      <div className="flex gap-2 border-b border-zinc-200 dark:border-zinc-700 pb-3">
        {PHASE_STEPS.map((step) => (
          <div
            key={step.key}
            className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
              phaseActive(phase, step.key)
                ? "bg-blue-600 text-white"
                : phaseDone(phase, step.key)
                ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200"
                : "bg-zinc-100 text-zinc-400 dark:bg-zinc-800 dark:text-zinc-500"
            }`}
          >
            {step.label}
          </div>
        ))}
      </div>

      {/* Planning phase */}
      {(phase === "planning" || options.length > 0) && (
        <div className="space-y-2">
          {options.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">
                Options Identified
              </h3>
              <div className="flex gap-2 mt-1">
                {options.map((opt) => (
                  <span
                    key={opt}
                    className="px-3 py-1 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-lg text-sm font-medium"
                  >
                    {opt}
                  </span>
                ))}
              </div>
            </div>
          )}
          {expertTasks.length > 0 && (
            <div>
              <h3 className="text-sm font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wide mt-3">
                Expert Tasks
              </h3>
              <ul className="mt-1 space-y-1">
                {expertTasks.map((task, i) => (
                  <li key={i} className="text-sm text-zinc-600 dark:text-zinc-300">
                    <span className="font-medium">{task.expert_role}:</span>{" "}
                    {task.deliverable}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Analysis phase — expert cards */}
      {Object.keys(expertOutputs).length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-zinc-500 dark:text-zinc-400 uppercase tracking-wide">
            Expert Analysis
          </h3>
          <div className="grid gap-3 mt-2">
            {Object.entries(expertOutputs).map(([role, output]) => (
              <ExpertCard key={role} output={output} options={options} />
            ))}
          </div>
        </div>
      )}

      {/* Conflicts phase */}
      {(conflicts.length > 0 || openQuestions.length > 0) && (
        <ConflictPanel
          conflicts={conflicts}
          openQuestions={openQuestions}
        />
      )}

      {/* Human gate — awaiting input */}
      {awaitingInput && onHumanFeedback && (
        <div className="border border-amber-300 dark:border-amber-600 rounded-lg p-4 bg-amber-50 dark:bg-amber-900/20">
          <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-200">
            Your Input Needed
          </h3>
          <p className="text-sm text-amber-700 dark:text-amber-300 mt-1">
            Review the expert analyses and conflicts above. You can approve and
            proceed, or request deeper analysis.
          </p>
          <textarea
            className="w-full mt-2 p-2 border rounded text-sm bg-white dark:bg-zinc-800 dark:border-zinc-600"
            rows={3}
            placeholder="Additional instructions (optional)..."
            value={feedbackText}
            onChange={(e) => setFeedbackText(e.target.value)}
          />
          <div className="flex gap-2 mt-2">
            <button
              className="px-4 py-1.5 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-700"
              onClick={() =>
                onHumanFeedback({
                  action: "proceed",
                  additional_instructions: feedbackText,
                })
              }
            >
              Proceed to Decision
            </button>
            <button
              className="px-4 py-1.5 bg-amber-600 text-white rounded text-sm font-medium hover:bg-amber-700"
              onClick={() =>
                onHumanFeedback({
                  action: "re_analyze",
                  additional_instructions: feedbackText,
                })
              }
            >
              Dig Deeper
            </button>
          </div>
        </div>
      )}

      {/* Recommendation phase */}
      {recommendation && (
        <RecommendationPanel
          recommendation={recommendation}
          options={options}
        />
      )}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add frontend/src/components/DecisionViewer.tsx
git commit -m "feat(frontend): add DecisionViewer component with phase stepper"
```

---

## Task 12: ExpertCard, ConflictPanel, RecommendationPanel Components

**Files:**
- Create: `frontend/src/components/ExpertCard.tsx`
- Create: `frontend/src/components/ConflictPanel.tsx`
- Create: `frontend/src/components/RecommendationPanel.tsx`

**Step 1: Create ExpertCard**

```tsx
// frontend/src/components/ExpertCard.tsx
import React from "react";
import type { ExpertOutput } from "../types";

interface ExpertCardProps {
  output: ExpertOutput;
  options: string[];
}

export function ExpertCard({ output, options }: ExpertCardProps) {
  return (
    <div className="border border-zinc-200 dark:border-zinc-700 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-semibold text-zinc-800 dark:text-zinc-200">
          {output.expert_role} Expert
        </h4>
        <span className="text-xs px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-500">
          Confidence: {(output.confidence * 100).toFixed(0)}%
        </span>
      </div>

      {/* Option ratings */}
      <div className="grid gap-2">
        {options.map((opt) => {
          const analysis = output.option_analyses?.[opt];
          if (!analysis) return null;
          return (
            <div
              key={opt}
              className="bg-zinc-50 dark:bg-zinc-800/50 rounded p-2"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-zinc-700 dark:text-zinc-300">
                  {opt}
                </span>
                <span className="text-sm font-bold text-blue-600 dark:text-blue-400">
                  {analysis.score}/10
                </span>
              </div>
              {analysis.claims.length > 0 && (
                <ul className="mt-1 text-xs text-zinc-600 dark:text-zinc-400 space-y-0.5">
                  {analysis.claims.map((claim, i) => (
                    <li key={i}>• {claim}</li>
                  ))}
                </ul>
              )}
              {analysis.risks.length > 0 && (
                <div className="mt-1 text-xs text-red-600 dark:text-red-400">
                  Risks: {analysis.risks.join(", ")}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Assumptions */}
      {output.assumptions.length > 0 && (
        <div className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
          <span className="font-medium">Assumptions:</span>{" "}
          {output.assumptions.join("; ")}
        </div>
      )}

      {/* Sources */}
      {output.sources.length > 0 && (
        <div className="mt-1 text-xs text-zinc-400">
          Sources: {output.sources.join(", ")}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Create ConflictPanel**

```tsx
// frontend/src/components/ConflictPanel.tsx
import React from "react";
import type { Conflict } from "../types";

interface ConflictPanelProps {
  conflicts: Conflict[];
  openQuestions: string[];
}

export function ConflictPanel({ conflicts, openQuestions }: ConflictPanelProps) {
  return (
    <div className="space-y-3">
      {conflicts.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-red-600 dark:text-red-400 uppercase tracking-wide">
            Conflicts Detected
          </h3>
          <div className="mt-2 space-y-2">
            {conflicts.map((c, i) => (
              <div
                key={i}
                className="border border-red-200 dark:border-red-800 rounded-lg p-3 bg-red-50 dark:bg-red-900/20"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs px-1.5 py-0.5 rounded bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-300 font-medium uppercase">
                    {c.conflict_type}
                  </span>
                  <span className="text-sm font-medium text-zinc-800 dark:text-zinc-200">
                    {c.topic}
                  </span>
                </div>
                <div className="flex gap-4 mt-1">
                  {c.experts.map((expert, j) => (
                    <div key={j} className="text-sm text-zinc-600 dark:text-zinc-400">
                      <span className="font-medium">{expert}:</span>{" "}
                      {c.values[j] || "N/A"}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {openQuestions.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-amber-600 dark:text-amber-400 uppercase tracking-wide">
            Open Questions
          </h3>
          <ul className="mt-1 space-y-1">
            {openQuestions.map((q, i) => (
              <li
                key={i}
                className="text-sm text-zinc-600 dark:text-zinc-300 pl-4 border-l-2 border-amber-300 dark:border-amber-600"
              >
                {q}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

**Step 3: Create RecommendationPanel**

```tsx
// frontend/src/components/RecommendationPanel.tsx
import React from "react";
import type { Recommendation } from "../types";

interface RecommendationPanelProps {
  recommendation: Recommendation;
  options: string[];
}

export function RecommendationPanel({
  recommendation,
  options,
}: RecommendationPanelProps) {
  const rec = recommendation;
  return (
    <div className="border-2 border-green-300 dark:border-green-700 rounded-lg p-4 bg-green-50 dark:bg-green-900/20">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-bold text-green-800 dark:text-green-200">
          Recommendation: {rec.recommended_option}
        </h3>
        <span className="text-sm px-2 py-0.5 rounded-full bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 font-medium">
          Confidence: {(rec.confidence * 100).toFixed(0)}%
        </span>
      </div>

      {/* Reasoning */}
      <div className="mb-3">
        <h4 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 uppercase">
          Why
        </h4>
        <ul className="mt-1 space-y-1">
          {rec.reasoning.map((r, i) => (
            <li key={i} className="text-sm text-zinc-700 dark:text-zinc-300">
              • {r}
            </li>
          ))}
        </ul>
      </div>

      {/* Tradeoff table */}
      <div className="mb-3">
        <h4 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 uppercase">
          Tradeoffs
        </h4>
        <div className="mt-2 grid gap-2">
          {options.map((opt) => {
            const t = rec.tradeoffs[opt];
            if (!t) return null;
            const isRecommended = opt === rec.recommended_option;
            return (
              <div
                key={opt}
                className={`rounded-lg p-3 ${
                  isRecommended
                    ? "bg-green-100 dark:bg-green-900/40 border border-green-300 dark:border-green-700"
                    : "bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700"
                }`}
              >
                <span className="text-sm font-semibold text-zinc-800 dark:text-zinc-200">
                  {opt} {isRecommended && "★"}
                </span>
                <div className="mt-1 grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="font-medium text-green-700 dark:text-green-400">
                      Pros:
                    </span>
                    <ul>
                      {t.pros?.map((p: string, i: number) => (
                        <li key={i} className="text-zinc-600 dark:text-zinc-400">
                          + {p}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <span className="font-medium text-red-700 dark:text-red-400">
                      Cons:
                    </span>
                    <ul>
                      {t.cons?.map((c: string, i: number) => (
                        <li key={i} className="text-zinc-600 dark:text-zinc-400">
                          - {c}
                        </li>
                      ))}
                    </ul>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Risks */}
      {rec.risks.length > 0 && (
        <div className="mb-3">
          <h4 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 uppercase">
            Remaining Risks
          </h4>
          <ul className="mt-1 space-y-0.5">
            {rec.risks.map((r, i) => (
              <li key={i} className="text-sm text-red-600 dark:text-red-400">
                ⚠ {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* What would change my mind */}
      {rec.what_would_change_mind.length > 0 && (
        <div>
          <h4 className="text-sm font-semibold text-zinc-600 dark:text-zinc-400 uppercase">
            What Would Change This Recommendation
          </h4>
          <ul className="mt-1 space-y-0.5">
            {rec.what_would_change_mind.map((w, i) => (
              <li
                key={i}
                className="text-sm text-zinc-600 dark:text-zinc-300 italic"
              >
                → {w}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
```

**Step 4: Commit**

```bash
git add frontend/src/components/ExpertCard.tsx frontend/src/components/ConflictPanel.tsx frontend/src/components/RecommendationPanel.tsx
git commit -m "feat(frontend): add ExpertCard, ConflictPanel, RecommendationPanel components"
```

---

## Task 13: Wire DecisionViewer into App.tsx

**Files:**
- Modify: `frontend/src/App.tsx` — Add decision mode handling
- Modify: `frontend/src/lib/discussionModes.ts` — Add Decision Assistant mode

**Step 1: Add mode to discussionModes.ts**

Add a new mode entry to the modes array in `frontend/src/lib/discussionModes.ts`:

```typescript
{
  id: "decision",
  name: "Decision Assistant",
  description: "Multi-expert analysis with conflict detection and structured recommendations",
  icon: "Scale",  // or appropriate icon from lucide-react
  category: "STRUCTURED",
  debateMode: null,  // Not a debate mode — uses separate endpoint
  defaultRounds: 0,
  stanceMode: "free",
  overrideUserPanelists: true,
  isDecisionMode: true,  // New flag to route to decision endpoint
}
```

**Step 2: Add decision state to App.tsx**

Add state variables near existing state declarations in App.tsx:

```typescript
// Decision assistant state
const [decisionPhase, setDecisionPhase] = useState<DecisionPhase>("planning");
const [decisionOptions, setDecisionOptions] = useState<string[]>([]);
const [decisionExpertTasks, setDecisionExpertTasks] = useState<ExpertTask[]>([]);
const [decisionExpertOutputs, setDecisionExpertOutputs] = useState<Record<string, ExpertOutput>>({});
const [decisionConflicts, setDecisionConflicts] = useState<Conflict[]>([]);
const [decisionOpenQuestions, setDecisionOpenQuestions] = useState<string[]>([]);
const [decisionRecommendation, setDecisionRecommendation] = useState<Recommendation | null>(null);
const [decisionAwaitingInput, setDecisionAwaitingInput] = useState(false);
```

**Step 3: Add decision stream handling in handleSend**

In the `handleSend` function, add a branch for the decision mode. Before the existing `askPanelStream` call, add:

```typescript
if (currentMode?.isDecisionMode) {
  // Decision Assistant flow
  setDecisionPhase("planning");
  setDecisionOptions([]);
  setDecisionExpertTasks([]);
  setDecisionExpertOutputs({});
  setDecisionConflicts([]);
  setDecisionOpenQuestions([]);
  setDecisionRecommendation(null);
  setDecisionAwaitingInput(false);

  await decisionStream(
    {
      thread_id: threadId,
      question: inputText,
      constraints: {},  // TODO: add constraints input UI
    },
    {
      onPhaseUpdate: (phase) => setDecisionPhase(phase),
      onOptionsIdentified: (options, tasks) => {
        setDecisionOptions(options);
        setDecisionExpertTasks(tasks);
        setDecisionPhase("analysis");
      },
      onExpertComplete: (role, output) => {
        setDecisionExpertOutputs((prev) => ({ ...prev, [role]: output }));
      },
      onConflictsDetected: (conflicts, questions) => {
        setDecisionConflicts(conflicts);
        setDecisionOpenQuestions(questions);
      },
      onAwaitingInput: () => {
        setDecisionAwaitingInput(true);
        setLoading(false);
      },
      onRecommendation: (rec) => {
        setDecisionRecommendation(rec);
        setDecisionPhase("done");
      },
      onError: (err) => console.error("Decision error:", err),
    },
    abortController?.signal
  );
  setLoading(false);
  return;
}
```

**Step 4: Add DecisionViewer rendering**

In the message display area, add DecisionViewer rendering when in decision mode:

```tsx
{currentMode?.isDecisionMode && (
  <DecisionViewer
    phase={decisionPhase}
    options={decisionOptions}
    expertTasks={decisionExpertTasks}
    expertOutputs={decisionExpertOutputs}
    conflicts={decisionConflicts}
    openQuestions={decisionOpenQuestions}
    recommendation={decisionRecommendation}
    awaitingInput={decisionAwaitingInput}
    onHumanFeedback={async (feedback) => {
      setDecisionAwaitingInput(false);
      setLoading(true);
      await decisionStream(
        {
          thread_id: threadId,
          question: "",
          resume: true,
          human_feedback: feedback,
        },
        {
          onPhaseUpdate: (phase) => setDecisionPhase(phase),
          onExpertComplete: (role, output) => {
            setDecisionExpertOutputs((prev) => ({ ...prev, [role]: output }));
          },
          onConflictsDetected: (conflicts, questions) => {
            setDecisionConflicts(conflicts);
            setDecisionOpenQuestions(questions);
          },
          onAwaitingInput: () => {
            setDecisionAwaitingInput(true);
            setLoading(false);
          },
          onRecommendation: (rec) => {
            setDecisionRecommendation(rec);
            setDecisionPhase("done");
          },
          onError: (err) => console.error("Decision error:", err),
        },
        abortController?.signal
      );
      setLoading(false);
    }}
  />
)}
```

**Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/lib/discussionModes.ts
git commit -m "feat(frontend): wire DecisionViewer into App with mode selector and SSE callbacks"
```

---

## Task 14: Remove AG2 Debate Engine

**Files:**
- Delete: `backend/debate/orchestrator.py`
- Delete: `backend/debate/agents.py`
- Delete: `backend/debate/evaluators.py`
- Delete: `backend/debate/scoring.py`
- Delete: `backend/debate/service.py`
- Delete: `backend/debate/usage.py`
- Modify: `backend/main.py` — Remove AG2 routes and imports
- Modify: `backend/pyproject.toml` — Remove ag2 dependency
- Delete: `backend/tests/test_ag2_debate.py`

**Step 1: Remove AG2 files**

```bash
rm backend/debate/orchestrator.py
rm backend/debate/agents.py
rm backend/debate/evaluators.py
rm backend/debate/scoring.py
rm backend/debate/service.py
rm backend/debate/usage.py
rm backend/tests/test_ag2_debate.py
```

**Step 2: Clean up main.py**

Remove from `backend/main.py`:
- The `_handle_ag2_debate()` function
- The AG2 service initialization code (`_ag2_service`, `AG2DebateService` imports)
- The `get_debate_engine()` routing in `ask_stream` (keep only LangGraph path for quick panel)
- Any imports from `debate.service`, `debate.orchestrator`, `debate.agents`

**Step 3: Remove ag2 dependency from pyproject.toml**

Remove these lines from `backend/pyproject.toml`:
```
"ag2>=0.3.0",
```

Also remove AG2-specific provider SDK deps if not needed by LangGraph:
```
"google-generativeai>=0.3.0",
"google-cloud-aiplatform>=1.38.0",
"pillow>=10.0.0",
"jsonschema>=4.0.0",
```

Keep: `langchain-openai`, `langchain-google-genai`, `langchain-anthropic`, `langgraph`, `langchain-tavily` (all used by decision system).

**Step 4: Remove debate engine config**

Remove `get_debate_engine()` from `backend/config.py` if no longer needed.

**Step 5: Verify nothing is broken**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/ -v --ignore=backend/tests/test_ag2_debate.py`
Expected: All remaining tests PASS

**Step 6: Commit**

```bash
git add -A
git commit -m "refactor: remove AG2 debate engine, keep LangGraph quick panel and decision assistant"
```

---

## Task 15: Integration Test — End-to-End Decision Flow

**Files:**
- Create: `backend/tests/test_decision_integration.py`

**Step 1: Write integration test**

```python
# backend/tests/test_decision_integration.py
"""
Integration test for the full decision graph.
Uses mocked LLMs to verify the graph flow works end-to-end.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from decision.graph import build_decision_graph


def _mock_llm_response(content: dict) -> MagicMock:
    resp = MagicMock()
    resp.content = json.dumps(content)
    resp.tool_calls = []
    return resp


@pytest.mark.asyncio
async def test_decision_graph_no_conflicts():
    """Full graph run: planner -> experts -> no conflicts -> synthesizer."""
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
```

**Step 2: Run integration test**

Run: `cd /home/david/Documents/projects/multi-agent-chat && PYTHONPATH=backend python -m pytest backend/tests/test_decision_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add backend/tests/test_decision_integration.py
git commit -m "test: add end-to-end integration test for decision graph"
```

---

## Summary

15 tasks covering the full build:

| # | Component | Type |
|---|-----------|------|
| 1 | Schemas + State | Backend foundation |
| 2 | Planner node | Backend node |
| 3 | Expert tools (search + calc) | Backend tools |
| 4 | Expert node (with Send) | Backend node |
| 5 | Conflict detector node | Backend node |
| 6 | Human gate node | Backend node |
| 7 | Synthesizer node | Backend node |
| 8 | Graph assembly | Backend graph |
| 9 | SSE endpoint | Backend API |
| 10 | Frontend types + API | Frontend |
| 11 | DecisionViewer | Frontend component |
| 12 | ExpertCard, ConflictPanel, RecommendationPanel | Frontend components |
| 13 | Wire into App.tsx | Frontend integration |
| 14 | Remove AG2 engine | Cleanup |
| 15 | Integration test | Testing |

Dependencies: Tasks 1-8 are sequential (each builds on prior). Task 9 depends on 8. Tasks 10-13 are sequential frontend work. Task 14 can happen anytime after 9. Task 15 depends on 8.
