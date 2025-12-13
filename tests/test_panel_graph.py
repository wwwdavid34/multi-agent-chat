"""Unit tests for the panel graph helpers."""
from __future__ import annotations

import os
from typing import Any, List

import pytest
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


def test_panelist_sequence_honors_custom_config(monkeypatch):
    alpha = StubModel("alpha")
    beta = StubModel("beta")

    def fake_factory(panelist, provider_keys):
        return alpha if panelist["name"] == "Alpha" else beta

    monkeypatch.setitem(panel_graph.PROVIDER_FACTORIES, "openai", fake_factory)

    config = {
        "configurable": {
            "panelists": [
                {"id": "1", "name": "Alpha", "provider": "openai", "model": "test-a"},
                {"id": "2", "name": "Beta", "provider": "openai", "model": "test-b"},
            ]
        }
    }

    state = {
        "messages": [HumanMessage(content="Hello")],
        "panel_responses": {},
        "summary": None,
    }

    result = panel_graph.panelist_sequence_node(state, config)

    assert result["panel_responses"]["Alpha"] == "alpha"
    assert result["panel_responses"]["Beta"] == "beta"
    assert len(alpha.invocations) == 1
    assert len(beta.invocations) == 1
    # Beta should see Alpha's reply in the conversation history.
    assert any(isinstance(msg, AIMessage) and msg.content == "alpha" for msg in beta.invocations[0])


def test_panelist_sequence_preserves_existing_responses(monkeypatch):
    stub = StubModel("new answer")
    monkeypatch.setitem(
        panel_graph.PROVIDER_FACTORIES,
        "openai",
        lambda panelist, provider_keys: stub,
    )

    state = {
        "messages": [HumanMessage(content="Follow-up?")],
        "panel_responses": {"first": "answer"},
        "summary": None,
    }

    result = panel_graph.panelist_sequence_node(state, None)

    assert result["panel_responses"]["first"] == "answer"
    default_name = panel_graph.DEFAULT_PANELISTS[0]["name"]
    assert result["panel_responses"][default_name] == "new answer"


def test_panelist_sequence_raises_for_unknown_provider():
    state = {
        "messages": [HumanMessage(content="Question")],
        "panel_responses": {},
        "summary": None,
    }

    config = {
        "configurable": {
            "panelists": [
                {"id": "x", "name": "X", "provider": "unknown", "model": "foo"},
            ]
        }
    }

    with pytest.raises(ValueError):
        panel_graph.panelist_sequence_node(state, config)
