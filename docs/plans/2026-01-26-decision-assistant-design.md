# Multi-Agent Decision Assistant — Design Document

**Date:** 2026-01-26
**Branch:** feature/topic-exploration
**Status:** Approved for implementation

## Overview

Replace the AG2 debate engine with a LangGraph-based decision assistant system. The system helps users make high-stakes decisions by decomposing questions, running parallel expert analysis, detecting conflicts, incorporating human feedback, and producing traceable recommendations.

Two modes survive:
1. **Quick Panel** — Single-round parallel expert responses (existing, cleaned up)
2. **Decision Assistant** — Multi-phase LangGraph graph (new, this design)

## Architecture

### Backend Structure

```
backend/
  main.py                    # FastAPI app, routes to mode
  decision/
    state.py                 # DecisionState TypedDict
    graph.py                 # LangGraph StateGraph definition
    schemas.py               # Pydantic models (ExpertOutput, Conflict, etc.)
    nodes/
      planner.py             # Decomposes question -> options + expert tasks
      expert.py              # Generic expert node (role-prompted, tool-enabled)
      conflict_detector.py   # Finds disagreements & gaps
      human_gate.py          # interrupt() for human feedback
      synthesizer.py         # Produces final recommendation
    tools/
      search.py              # Tavily web search
      calculator.py          # Python code execution for calculations
  panel/
    (cleaned up quick-panel code)
```

### Design Principles

- **Graph, not chat** — Structured LangGraph StateGraph with typed state
- **Experts do not talk to each other** — Each expert analyzes independently
- **No free-form summarization** — Structured schemas enforce substance
- **Human intervenes at decision boundaries** — Not mid-analysis
- **Forced commitment** — Experts must commit to positions, not hedge

## State Model

### DecisionState (LangGraph TypedDict)

```python
class DecisionState(TypedDict):
    # Input
    user_question: str
    constraints: dict                    # budget, timeline, risk tolerance

    # Planner output
    decision_options: list[str]          # ["Build", "Buy", "Partner"]
    expert_tasks: list[ExpertTask]       # who analyzes what

    # Expert outputs (reducer: merge dicts)
    expert_outputs: Annotated[dict[str, ExpertOutput], merge_dicts]

    # Conflict detection
    conflicts: list[Conflict]
    open_questions: list[str]

    # Human-in-the-loop
    human_feedback: Optional[HumanFeedback]
    requires_human_input: bool

    # Iteration control
    iteration: int                       # expert->conflict loop count
    max_iterations: int                  # cap at 2-3

    # Final output
    recommendation: Optional[Recommendation]
    phase: str                           # planning|analysis|conflict|human|synthesis|done
```

### Pydantic Schemas

```python
class ExpertTask(BaseModel):
    expert_role: str          # "Finance", "Market", "Risk", "Tech"
    deliverable: str          # "5yr cost model per option"

class ExpertOutput(BaseModel):
    expert_role: str
    option_analyses: dict[str, OptionAnalysis]
    assumptions: list[str]
    sources: list[str]
    confidence: float         # 0.0-1.0

class OptionAnalysis(BaseModel):
    option: str
    claims: list[str]
    numbers: dict[str, Any]
    risks: list[str]
    score: float              # 0-10

class Conflict(BaseModel):
    conflict_type: str        # "numeric", "assumption", "risk_assessment"
    topic: str
    experts: list[str]
    values: list[str]

class Recommendation(BaseModel):
    recommended_option: str
    reasoning: list[str]
    tradeoffs: dict[str, dict]  # option -> {pros, cons}
    risks: list[str]
    what_would_change_mind: list[str]
    confidence: float
```

## Graph Structure

```
START -> planner -> expert_agents (parallel via Send()) -> conflict_detector -> [conditional]
                                                                                 |-> conflicts found -> human_gate -> [conditional]
                                                                                 |                                     |-> re-analyze -> expert_agents
                                                                                 |                                     |-> proceed -> synthesizer -> END
                                                                                 |-> no conflicts -> synthesizer -> END
```

### Node 1: Planner

- **Type:** LLM-only (no tools)
- **Input:** user_question, constraints
- **Output:** decision_options, expert_tasks
- **Model:** GPT-4o with structured output (JSON mode)
- Decomposes the question into concrete options and assigns expert roles with specific deliverables

### Node 2: Expert Agents (parallel)

- **Type:** LLM + tools
- **Execution:** Parallel via LangGraph `Send()` API (fan-out)
- **Input:** ExpertTask + decision_options + constraints
- **Output:** ExpertOutput (structured, per-option analysis)
- **Tools:** Tavily search, Python calculator
- **Prompt enforces:** Specific numbers (not ranges), explicit assumptions, per-option ratings, source citations, committed positions

Generic node — one `run_expert` function parameterized by ExpertTask:

```python
async def run_expert(state: DecisionState, config: RunnableConfig) -> dict:
    task: ExpertTask = config["configurable"]["task"]
    system_prompt = EXPERT_SYSTEM_PROMPT.format(
        role=task.expert_role,
        deliverable=task.deliverable,
        options=state["decision_options"],
        constraints=state["constraints"],
    )
    llm = ChatOpenAI(model="gpt-4o").bind_tools([search_tool, calculator_tool])
    result = await llm.ainvoke(messages, response_format=ExpertOutput)
    return {"expert_outputs": {task.expert_role: result}}
```

### Node 3: Conflict Detector

- **Type:** LLM + rules
- **Input:** expert_outputs
- **Output:** conflicts, open_questions
- Detects: numeric disagreements (>20% delta), assumption mismatches, coverage gaps
- Does NOT resolve conflicts — only surfaces them

### Node 4: Human Gate

- **Type:** LangGraph `interrupt()`
- **Triggers when:** conflicts detected
- **User sees:** options table, expert analyses, conflicts, open questions
- **User can:** approve assumptions, request re-analysis, remove options, override constraints
- **Routing:** if "dig deeper" and iteration < max_iterations -> loop to experts; else -> synthesizer

### Node 5: Synthesizer

- **Type:** LLM-only
- **Input:** expert_outputs, conflicts, human_feedback
- **Output:** Recommendation
- NOT a summarizer — compares options head-to-head using expert data
- Must produce: recommended option, reasoning, tradeoffs per option, risks, "what would change my mind", confidence score

## Expert Tools

### Tavily Search
- Web search returning raw results
- Expert interprets and cites sources
- Returns structured search results, not prose

### Python Calculator
- Executes Python expressions
- For financial projections, comparisons, unit conversions
- Returns raw computation results

Tools are only callable by expert nodes. Planner and Synthesizer are LLM-only.

## Frontend

### New Components

- `DecisionViewer.tsx` — Phase-driven main viewer with stepper
- `ExpertCard.tsx` — Expert analysis display card
- `ConflictPanel.tsx` — Conflict and open question display
- `RecommendationPanel.tsx` — Final decision display

### Layout

```
+-----------------------------------------------------+
|  Question + Constraints                              |
+-----------------------------------------------------+
|  Phase: [Planning] [Analysis] [Conflicts] [Decision] |  <- stepper
+-----------------------------------------------------+
|  Phase-specific content:                             |
|  Planning:  Options list + expert task assignments   |
|  Analysis:  Expert cards streaming in parallel       |
|  Conflicts: Conflict list + open questions           |
|             + Human input area (when gate active)    |
|  Decision:  Recommendation + tradeoff table          |
|             + "what would change my mind"            |
+-----------------------------------------------------+
```

### SSE Event Mapping

| Backend Phase | SSE Event Type       | Frontend Action                    |
|---------------|----------------------|------------------------------------|
| planning      | phase_update         | Show options, expert task list      |
| planning      | options_identified   | Populate options display            |
| analysis      | expert_streaming     | Stream expert card content          |
| analysis      | expert_complete      | Show structured expert output       |
| conflict      | conflicts_detected   | Show conflict highlights            |
| conflict      | open_questions       | Show unresolved issues              |
| human         | awaiting_input       | Show input form with context        |
| synthesis     | recommendation       | Show final decision panel           |
| done          | done                 | Mark complete                       |

Communication remains SSE (Server-Sent Events) over HTTP, same as current system.

## Migration

### Remove
- `backend/debate/orchestrator.py` — AG2 GroupChat orchestration
- `backend/debate/agents.py` — AG2 agent creation
- `backend/debate/evaluators.py` — Debate-specific evaluation (stances, arguments)
- `backend/debate/scoring.py` — Point system, forced concessions
- `backend/debate/service.py` — AG2 debate service
- AG2 dependency

### Keep & Adapt
- `backend/main.py` — Refactor routes, add `/decision-stream` endpoint
- `backend/panel_graph.py` — Quick-panel code (evaluate: reuse or rewrite)
- `backend/debate/persistence.py` — Adapt for DecisionState storage
- Frontend SSE infrastructure (`EventSource` pattern)
- `PanelConfigurator.js`, `Markdown.js`, auth, theme, env config

### New
- `backend/decision/` — Full new module
- `frontend/src/components/DecisionViewer.tsx`
- `frontend/src/components/ExpertCard.tsx`
- `frontend/src/components/ConflictPanel.tsx`
- `frontend/src/components/RecommendationPanel.tsx`

## Build Order

1. **Backend foundation:** State + schemas -> Graph skeleton -> Planner node -> Expert node (1 expert, no tools) -> SSE wiring
2. **Frontend shell:** DecisionViewer -> Planning phase -> Analysis phase with streaming
3. **Backend depth:** Add tools (search, calc) -> Remaining experts -> Conflict detector -> Synthesizer
4. **Frontend depth:** Conflict panel -> Human gate UI -> Recommendation panel
5. **Integration:** Human-in-the-loop flow -> Persistence -> Polish

## Litmus Test

After running the system, ask:
> "If I disagree with the conclusion, can I point to exactly which assumption I reject?"

If yes — it's a real decision assistant.
If no — it's still a chatbot.
