# 📘 **Software Design Document (SDD)**

## **AI Multi-Agent Discussion Panel System**

### *(LangGraph + FastAPI + Postgres Memory)*

---

# 1. **Overview**

The AI Multi-Agent Discussion Panel System enables multiple LLM models (“panelists”) to answer a user question, followed by a moderator model that synthesizes and consolidates their answers into a final output.
The system maintains **stateful, multi-turn memory** so each panelist and moderator remembers the entire discussion across follow-up questions.

The orchestration is built using **LangGraph**, exposing an HTTP API via **FastAPI**, with conversation state persisted using a **Postgres checkpointer**.

---

# 2. **Goals**

### 2.1 Functional Goals

* Allow user to ask questions to a panel of LLMs.
* For each turn:

  1. User question is added to shared memory.
  2. All panelist agents respond.
  3. A moderator agent consolidates responses.
* All agents must remember prior turns.
* User can ask follow-up questions in the same thread.
* Backend exposes simple `/ask` API.
* Frontend can retrieve panelist responses + consolidated summary.

### 2.2 Non-Functional Goals

* Code-first architecture with clear extensibility.
* Deterministic data flow using LangGraph state machine.
* Modular agent definitions.
* Production-ready persistent memory (Postgres).
* Easy to integrate with any frontend.

---

# 3. **System Architecture**

```
          ┌────────────┐
          │   Frontend │
          └──────┬─────┘
                 │ HTTP /ask
          ┌──────▼──────────────────────────┐
          │            FastAPI              │
          └──────┬──────────────────────────┘
                 │ invokes graph.invoke()
  thread_id → ┌──▼─────────────────────────────────┐
              │            LangGraph               │
              │     (State Graph Engine)          │
              └──┬────────────────────────────────┘
                 │ loads/saves memory (checkpointer)
         ┌───────▼───────────────────────────────────────┐
         │                 Postgres DB                    │
         │   (graph checkpoints + message histories)      │
         └───────────────────────────────────────────────┘
```

---

# 4. **State Model**

A LangGraph state object holds the global context.

```python
class PanelState(TypedDict):
    # Full conversation history (user + agents + moderator)
    messages: Annotated[List[AnyMessage], add_messages]

    # Per-turn responses from all panelist models
    panel_responses: Dict[str, str]   # {agent_name: text}

    # Final moderator-reviewed consolidated answer
    summary: Optional[str]
```

### 4.1 Message Flow Rules

* Incoming user input adds a `HumanMessage`.
* Each panelist appends an `AIMessage`.
* Moderator appends an `AIMessage`.
* LangGraph’s `add_messages` ensures automatic accumulation.

---

# 5. **Agents**

## 5.1 Panelist Agents

* Each agent:

  * Receives full `messages` history.
  * Produces one answer per turn.
  * Writes to `panel_responses[agent_name]`.

## 5.2 Moderator Agent

* Reads all `panel_responses`.
* Reads full `messages` for context.
* Produces:

  * Consolidated final answer.
  * Reflection on disagreements.
* Writes result to `summary`.

---

# 6. **Workflow (Graph Topology)**

Sequential execution:

```
START
  ↓
panelist_gpt4o
  ↓
panelist_gpt4o_strict
  ↓
panelist_others (optional, extendable)
  ↓
moderator
  ↓
END
```

This design is intentionally simple for Codex; future branches, loops, and parallelism may be added.

---

# 7. **Checkpointer (Memory Persistence)**

Use **PostgresSaver** for production:

* Each conversation has a `thread_id`.
* Each turn:

  * LangGraph loads previous state from Postgres.
  * New HumanMessage is merged in.
  * The graph executes.
  * New checkpoint saved.

The checkpointer ensures:

* Crash-safe state.
* Persistent memory across server restarts.
* Horizontal scalability.

---

# 8. **API Specification (FastAPI)**

### **POST /ask**

Request:

```json
{
  "thread_id": "string",
  "question": "string"
}
```

Response:

```json
{
  "thread_id": "string",
  "summary": "string",
  "panel_responses": {
    "agent_name": "agent response text"
  }
}
```

---

# 9. **Implementation Plan**

This section contains the exact code structure Codex should generate.

---

## 9.1 **File: `panel_graph.py`**

### Responsibilities:

* Define state.
* Create panelist nodes.
* Create moderator node.
* Build LangGraph with sequential edges.
* Initialize PostgresSaver checkpointer.

### Code Skeleton:

```python
from typing import Dict, List, Optional, Annotated
from typing_extensions import TypedDict

from langchain_core.messages import AnyMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph_checkpoint_postgres import PostgresSaver

import os

# 1. State -----------------------------------------------------------

class PanelState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages]
    panel_responses: Dict[str, str]
    summary: Optional[str]

# 2. Models ----------------------------------------------------------

panelist_models: Dict[str, ChatOpenAI] = {
    "gpt4o": ChatOpenAI(model="gpt-4o-mini", temperature=0.2),
    "gpt4o_strict": ChatOpenAI(model="gpt-4o", temperature=0.0),
}

moderator_model = ChatOpenAI(model="gpt-4o", temperature=0.1)

# 3. Panelist Node Factory ------------------------------------------

def make_panelist_node(agent_name: str, model: ChatOpenAI):
    def node(state: PanelState) -> Dict:
        messages = state["messages"]
        response = model.invoke(messages)

        panel_responses = dict(state.get("panel_responses", {}))
        panel_responses[agent_name] = response.content

        return {
            "messages": [response],
            "panel_responses": panel_responses
        }
    return node

# 4. Moderator Node -------------------------------------------------

def moderator_node(state: PanelState) -> Dict:
    panel_responses = state.get("panel_responses", {})
    messages = state.get("messages", [])

    panel_text = "\n\n".join(
        f"{name}:\n{resp}"
        for name, resp in panel_responses.items()
    )

    moderator_prompt = (
        "You are moderating a panel of expert AI agents.\n"
        "Provide a final consolidated answer.\n"
        "Highlight agreements and disagreements.\n\n"
        f"Panel responses:\n{panel_text}"
    )

    response = moderator_model.invoke(messages + [HumanMessage(content=moderator_prompt)])

    return {
        "messages": [response],
        "summary": response.content
    }

# 5. Graph Build -----------------------------------------------------

def build_panel_graph():
    builder = StateGraph(PanelState)

    # panelists
    prev = START
    for name, model in panelist_models.items():
        node_name = f"panelist_{name}"
        builder.add_node(node_name, make_panelist_node(name, model))
        builder.add_edge(prev, node_name)
        prev = node_name

    # moderator
    builder.add_node("moderator", moderator_node)
    builder.add_edge(prev, "moderator")
    builder.add_edge("moderator", END)

    # Postgres Backing Store
    pg_url = os.environ["PG_CONN_STR"]
    checkpointer = PostgresSaver.from_conn_string(pg_url)

    return builder.compile(checkpointer=checkpointer)

panel_graph = build_panel_graph()
```

---

## 9.2 **File: `main.py`**

```python
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from panel_graph import panel_graph

app = FastAPI(title="AI Discussion Panel")

class AskRequest(BaseModel):
    thread_id: str
    question: str

class AskResponse(BaseModel):
    thread_id: str
    summary: str
    panel_responses: dict

@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    state = {
        "messages": [HumanMessage(content=req.question)],
        "panel_responses": {},
        "summary": None
    }

    config = {"configurable": {"thread_id": req.thread_id}}
    result = panel_graph.invoke(state, config=config)

    return AskResponse(
        thread_id=req.thread_id,
        summary=result["summary"],
        panel_responses=result["panel_responses"]
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

# 10. **Environment Variables**

```
OPENAI_API_KEY=<your api key>
PG_CONN_STR=postgresql://user:pass@host:5432/dbname
```

---

# 11. **Testing Plan**

### 11.1 Unit Tests

* Test that each panelist node appends an AIMessage.
* Test moderator generates a summary.
* Test state accumulation across turns.
* Test Postgres checkpointer loads/saves consistently.

### 11.2 Integration Tests

* Simulate multi-turn conversation with same `thread_id`.
* Ensure panelist messages are visible to next turns.
* Confirm API returns expected JSON structure.

---

# 12. **Future Extensions**

* Add more panelists (Anthropic, Gemini, local models, etc.)
* Add debate cycles (loops in LangGraph)
* Parallel execution of panelists
* Confidence scoring and vote-weighting
* Human review nodes
* Front-end visualization of panel differences
* Multi-user session management with RBAC

