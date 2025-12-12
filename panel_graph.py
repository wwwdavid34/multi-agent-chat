"""LangGraph orchestration for the AI multi-agent discussion panel."""
from __future__ import annotations

import logging
from typing import Annotated, Dict, List, Optional

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict

from config import get_openai_api_key, get_pg_conn_str, use_in_memory_checkpointer


logger = logging.getLogger(__name__)

class PanelState(TypedDict):
    """State shared across all nodes in the discussion graph."""

    messages: Annotated[List[AnyMessage], add_messages]
    panel_responses: Dict[str, str]
    summary: Optional[str]


get_openai_api_key()

panelist_models: Dict[str, ChatOpenAI] = {
    "gpt4o": ChatOpenAI(model="gpt-4o-mini", temperature=0.2),
    "gpt4o_strict": ChatOpenAI(model="gpt-4o", temperature=0.0),
}

moderator_model = ChatOpenAI(model="gpt-4o", temperature=0.1)


def make_panelist_node(agent_name: str, model: ChatOpenAI):
    """Create a LangGraph node that runs a single panelist model."""

    def node(state: PanelState) -> Dict[str, object]:
        messages = state["messages"]
        response: AIMessage = model.invoke(messages)

        panel_responses = dict(state.get("panel_responses", {}))
        panel_responses[agent_name] = response.content

        return {
            "messages": [response],
            "panel_responses": panel_responses,
        }

    return node


def moderator_node(state: PanelState) -> Dict[str, object]:
    panel_responses = state.get("panel_responses", {})
    messages = state.get("messages", [])

    panel_text = "\n\n".join(
        f"{name}:\n{resp}" for name, resp in panel_responses.items()
    )

    moderator_prompt = (
        "You are moderating a panel of expert AI agents.\n"
        "Provide a final consolidated answer.\n"
        "Highlight agreements and disagreements.\n\n"
        f"Panel responses:\n{panel_text}"
    )

    response = moderator_model.invoke(
        messages + [HumanMessage(content=moderator_prompt)]
    )

    return {
        "messages": [response],
        "summary": response.content,
    }


def build_panel_graph():
    builder = StateGraph(PanelState)

    prev = START
    for name, model in panelist_models.items():
        node_name = f"panelist_{name}"
        builder.add_node(node_name, make_panelist_node(name, model))
        builder.add_edge(prev, node_name)
        prev = node_name

    builder.add_node("moderator", moderator_node)
    builder.add_edge(prev, "moderator")
    builder.add_edge("moderator", END)

    if use_in_memory_checkpointer():
        checkpointer = MemorySaver()
    else:
        try:
            from langgraph_checkpoint_postgres import PostgresSaver
        except ModuleNotFoundError:  # pragma: no cover - fallback for new langgraph releases
            from langgraph.checkpoint.postgres import PostgresSaver

        try:
            pg_url = get_pg_conn_str()
            checkpointer = PostgresSaver.from_conn_string(pg_url)
        except Exception as exc:  # pragma: no cover - fallback in local envs
            logger.warning("Falling back to in-memory checkpointer: %s", exc)
            checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


panel_graph = build_panel_graph()
