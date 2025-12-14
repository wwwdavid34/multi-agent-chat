"""LangGraph orchestration for the AI multi-agent discussion panel."""
from __future__ import annotations

import logging
import asyncio
from typing import Annotated, Any, Callable, Dict, Iterable, List, Optional

import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, AnyMessage, BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import Protocol, TypedDict

from config import (
    get_claude_api_key,
    get_gemini_api_key,
    get_grok_api_key,
    get_openai_api_key,
    get_pg_conn_str,
    use_in_memory_checkpointer,
)


logger = logging.getLogger(__name__)

class PanelState(TypedDict):
    """State shared across all nodes in the discussion graph."""

    messages: Annotated[List[AnyMessage], add_messages]
    panel_responses: Dict[str, str]
    summary: Optional[str]


class PanelistConfig(TypedDict):
    id: str
    name: str
    provider: str
    model: str


DEFAULT_PANELISTS: List[PanelistConfig] = [
    {
        "id": "panelist-default-1",
        "name": "GPT-4o Mini",
        "provider": "openai",
        "model": "gpt-4o-mini",
    },
    {
        "id": "panelist-default-2",
        "name": "GPT-4o",
        "provider": "openai",
        "model": "gpt-4o",
    },
]


PROVIDER_DEFAULT_MODELS: Dict[str, str] = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-1.5-flash",
    "claude": "claude-3-haiku-20240307",
    "grok": "grok-beta",
}


class PanelistRunner(Protocol):
    def invoke(self, messages: List[AnyMessage]) -> AIMessage:  # pragma: no cover - protocol
        ...

    async def ainvoke(self, messages: List[AnyMessage]) -> AIMessage:  # pragma: no cover - protocol
        ...


class GrokChatRunner:
    """Minimal runner for xAI's Grok chat completion API."""

    api_url = "https://api.x.ai/v1/chat/completions"

    def __init__(self, model: str, api_key: str, temperature: float) -> None:
        self.model = model
        self.api_key = api_key
        self.temperature = temperature

    def invoke(self, messages: List[AnyMessage]) -> AIMessage:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": _to_openai_messages(messages),
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=30.0) as client:
            response = client.post(self.api_url, json=payload, headers=headers)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:  # pragma: no cover - network failures
                raise RuntimeError(f"Grok request failed: {response.text}") from exc

        data = response.json()
        content = _extract_grok_content(data)
        if not content:
            raise RuntimeError("Grok returned an empty response")
        return AIMessage(content=content)

    async def ainvoke(self, messages: List[AnyMessage]) -> AIMessage:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": _to_openai_messages(messages),
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.api_url, json=payload, headers=headers)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:  # pragma: no cover - network failures
                raise RuntimeError(f"Grok request failed: {response.text}") from exc

        data = response.json()
        content = _extract_grok_content(data)
        if not content:
            raise RuntimeError("Grok returned an empty response")
        return AIMessage(content=content)


def _to_openai_messages(messages: Iterable[BaseMessage]) -> List[Dict[str, str]]:
    as_dicts: List[Dict[str, str]] = []
    for message in messages:
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            role = "system"
        as_dicts.append({"role": role, "content": _message_content_as_text(message)})
    return as_dicts


def _message_content_as_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return str(content)


def _extract_grok_content(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return ""


ProviderFactory = Callable[[PanelistConfig, Dict[str, str]], PanelistRunner]


def _create_openai_runner(panelist: PanelistConfig, provider_keys: Dict[str, str]) -> PanelistRunner:
    model_name = panelist["model"] or PROVIDER_DEFAULT_MODELS["openai"]
    api_key = _provider_key("openai", provider_keys, get_openai_api_key)
    return ChatOpenAI(model=model_name, temperature=0.2, api_key=api_key)


def _create_gemini_runner(panelist: PanelistConfig, provider_keys: Dict[str, str]) -> PanelistRunner:
    model_name = panelist["model"] or PROVIDER_DEFAULT_MODELS["gemini"]
    api_key = _provider_key("gemini", provider_keys, get_gemini_api_key)
    return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=0.2)


def _create_claude_runner(panelist: PanelistConfig, provider_keys: Dict[str, str]) -> PanelistRunner:
    model_name = panelist["model"] or PROVIDER_DEFAULT_MODELS["claude"]
    api_key = _provider_key("claude", provider_keys, get_claude_api_key)
    return ChatAnthropic(model=model_name, temperature=0.2, anthropic_api_key=api_key)


def _create_grok_runner(panelist: PanelistConfig, provider_keys: Dict[str, str]) -> PanelistRunner:
    model_name = panelist["model"] or PROVIDER_DEFAULT_MODELS["grok"]
    api_key = _provider_key("grok", provider_keys, get_grok_api_key)
    return GrokChatRunner(model=model_name, api_key=api_key, temperature=0.2)


PROVIDER_FACTORIES: Dict[str, ProviderFactory] = {
    "openai": _create_openai_runner,
    "gemini": _create_gemini_runner,
    "claude": _create_claude_runner,
    "grok": _create_grok_runner,
}


get_openai_api_key()

moderator_model = ChatOpenAI(model="gpt-4o", temperature=0.1, api_key=get_openai_api_key())


async def panelist_sequence_node(state: PanelState, config: Optional[RunnableConfig] = None) -> Dict[str, object]:
    """Run each configured panelist in parallel and collect responses."""

    panel_configs = _resolve_panelists(config)
    provider_keys = _resolve_provider_keys(config)
    panel_responses = dict(state.get("panel_responses", {}))
    history: List[AnyMessage] = list(state.get("messages", []))
    new_messages: List[AnyMessage] = []

    runners = [_build_runner(p, provider_keys) for p in panel_configs]
    
    # Run all panelists in parallel
    results = await asyncio.gather(*(runner.ainvoke(history) for runner in runners))

    for panelist, response in zip(panel_configs, results):
        new_messages.append(response)
        panel_responses[panelist["name"]] = response.content

    return {
        "messages": new_messages,
        "panel_responses": panel_responses,
    }


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


def _resolve_panelists(config: Optional[RunnableConfig]) -> List[PanelistConfig]:
    configurable = {}
    if config and isinstance(config, dict):
        configurable = config.get("configurable") or {}

    raw_panelists = configurable.get("panelists")
    if isinstance(raw_panelists, list) and raw_panelists:
        source = raw_panelists
    else:
        source = DEFAULT_PANELISTS

    resolved: List[PanelistConfig] = []
    for index, entry in enumerate(source):
        resolved.append(_sanitize_panelist(entry, index))
    return resolved


def _resolve_provider_keys(config: Optional[RunnableConfig]) -> Dict[str, str]:
    configurable = {}
    if config and isinstance(config, dict):
        configurable = config.get("configurable") or {}
    raw_keys = configurable.get("provider_keys")
    provider_keys: Dict[str, str] = {}
    if isinstance(raw_keys, dict):
        for key, value in raw_keys.items():
            if isinstance(value, str) and value.strip():
                provider_keys[key.lower()] = value.strip()
    return provider_keys


def _sanitize_panelist(entry: Any, index: int) -> PanelistConfig:
    if not isinstance(entry, dict):
        raise ValueError("Each panelist must be an object")

    provider = str(entry.get("provider") or "openai").lower().strip()
    if provider not in PROVIDER_FACTORIES:
        raise ValueError(f"Unsupported provider: {provider}")

    default_model = PROVIDER_DEFAULT_MODELS.get(provider, PROVIDER_DEFAULT_MODELS["openai"])
    model = str(entry.get("model") or default_model).strip() or default_model
    name = str(entry.get("name") or f"Panelist {index + 1}").strip() or f"Panelist {index + 1}"
    identifier = str(entry.get("id") or f"panelist-{index + 1}").strip() or f"panelist-{index + 1}"

    return {
        "id": identifier,
        "name": name,
        "provider": provider,
        "model": model,
    }


def _build_runner(panelist: PanelistConfig, provider_keys: Dict[str, str]) -> PanelistRunner:
    provider = panelist["provider"].lower()
    factory = PROVIDER_FACTORIES.get(provider)
    if not factory:
        raise ValueError(f"Unsupported provider: {provider}")
    return factory(panelist, provider_keys)


def _provider_key(provider: str, provider_keys: Dict[str, str], fallback: Callable[[], str]) -> str:
    sanitized = provider.lower()
    key = provider_keys.get(sanitized)
    if key:
        return key
    return fallback()


def build_panel_graph():
    builder = StateGraph(PanelState)

    builder.add_node("panelists", panelist_sequence_node)
    builder.add_edge(START, "panelists")
    builder.add_node("moderator", moderator_node)
    builder.add_edge("panelists", "moderator")
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
