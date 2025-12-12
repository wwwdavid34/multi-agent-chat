"""Unit tests for the panel graph helpers."""
from __future__ import annotations

import os
from typing import Any, List

from langchain_core.messages import AIMessage, HumanMessage

# Ensure imports use an in-memory checkpointer and test keys.
os.environ.setdefault("USE_IN_MEMORY_CHECKPOINTER", "1")
os.environ.setdefault("OPENAI_API_KEY", "test-key")

import importlib

panel_graph = importlib.import_module("panel_graph")


class StubModel:
    def __init__(self, reply: str):
        self.reply = reply
        self.invocations: List[List[Any]] = []

    def invoke(self, messages: List[Any]) -> AIMessage:
        self.invocations.append(messages)
        return AIMessage(content=self.reply)


def test_panelist_node_appends_response(monkeypatch):
    stub = StubModel("panel answer")
    node = panel_graph.make_panelist_node("stub", stub)

    state = {
        "messages": [HumanMessage(content="Question?")],
        "panel_responses": {},
        "summary": None,
    }

    result = node(state)

    assert result["panel_responses"]["stub"] == "panel answer"
    assert isinstance(result["messages"][0], AIMessage)


def test_moderator_node_produces_summary(monkeypatch):
    stub = StubModel("final summary")
    monkeypatch.setattr(panel_graph, "moderator_model", stub)

    state = {
        "messages": [HumanMessage(content="Hi")],
        "panel_responses": {"agent": "response"},
        "summary": None,
    }

    result = panel_graph.moderator_node(state)

    assert result["summary"] == "final summary"
    # Ensure moderator sees prior panelist output in prompt.
    assert stub.invocations
    assert any("agent" in msg.content for msg in stub.invocations[-1] if isinstance(msg, HumanMessage))


def test_panelist_node_preserves_existing_responses():
    stub = StubModel("another answer")
    node = panel_graph.make_panelist_node("second", stub)

    state = {
        "messages": [HumanMessage(content="Follow-up?")],
        "panel_responses": {"first": "answer"},
        "summary": None,
    }

    result = node(state)

    assert result["panel_responses"]["first"] == "answer"
    assert result["panel_responses"]["second"] == "another answer"
