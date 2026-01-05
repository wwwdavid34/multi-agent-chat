import asyncio
import pytest

from debate import orchestrator as orch
from debate import agents as agent_mod


class _StubAssistant:
    def __init__(self, name="agent", system_message=None, llm_config=None, human_input_mode=None):
        self.name = name
        self.system_message = system_message
        self.llm_config = llm_config
        self.human_input_mode = human_input_mode

    def generate_reply(self, *_, **__):
        return ""


@pytest.mark.asyncio
async def test_groupchat_manager_prefers_gemini_when_available(monkeypatch):
    """Ensure GroupChatManager uses Gemini config when only Gemini key is provided."""

    captured_config = {}

    # Stubs to avoid calling real AG2
    monkeypatch.setattr(agent_mod, "create_panelist_agent", lambda cfg, key: _StubAssistant(name=cfg.get("name", "P1")))
    monkeypatch.setattr(agent_mod, "create_moderator_agent", lambda: _StubAssistant(name="Moderator"))
    monkeypatch.setattr(orch, "GroupChat", lambda agents, messages, max_round: _StubAssistant(name="GC"))

    def _fake_gcm(groupchat, llm_config, is_termination_msg):
        captured_config["config_list"] = llm_config.get("config_list")
        return _StubAssistant(name="GCM")

    monkeypatch.setattr(orch, "GroupChatManager", _fake_gcm)

    # Force OpenAI key retrieval to fail so we verify fallback ordering
    monkeypatch.setattr(orch, "get_openai_api_key", lambda: (_ for _ in ()).throw(RuntimeError("no openai")))
    monkeypatch.setattr(orch, "get_gemini_api_key", lambda: "GEMINI_KEY")
    monkeypatch.setattr(orch, "get_claude_api_key", lambda: (_ for _ in ()).throw(RuntimeError("no claude")))
    monkeypatch.setattr(orch, "get_grok_api_key", lambda: (_ for _ in ()).throw(RuntimeError("no grok")))

    state = {
        "thread_id": "t",
        "phase": "init",
        "debate_round": 0,
        "max_rounds": 1,
        "consensus_reached": False,
        "panelists": [{"name": "P1", "provider": "google", "model": "gemini-1.5-flash"}],
        "provider_keys": {"google": "GEMINI_KEY"},
    }
    q = asyncio.Queue()
    orch_instance = orch.DebateOrchestrator(state, q)

    await orch_instance.initialize()

    assert captured_config["config_list"] == [
        {"model": "gemini-1.5-flash", "api_key": "GEMINI_KEY", "api_type": "google"}
    ]


def test_panelist_agent_sets_api_type_for_gemini(monkeypatch):
    """Agent factory should set api_type correctly for Gemini."""
    created = {}

    def _fake_assistant(name, system_message, llm_config, human_input_mode):
        created["llm_config"] = llm_config
        created["name"] = name
        return _StubAssistant(name=name, system_message=system_message, llm_config=llm_config)

    monkeypatch.setattr(agent_mod, "AssistantAgent", _fake_assistant)

    agent_mod.create_panelist_agent(
        {"name": "GeminiPanel", "provider": "google", "model": "gemini-1.5-flash"},
        api_key="GEMINI_KEY",
    )

    cfg = created["llm_config"]["config_list"][0]
    assert cfg["api_type"] == "google"
    assert cfg["api_key"] == "GEMINI_KEY"
    assert cfg["model"] == "gemini-1.5-flash"


def test_panelist_agent_sets_api_type_for_claude(monkeypatch):
    """Agent factory should set api_type correctly for Claude."""
    created = {}

    def _fake_assistant(name, system_message, llm_config, human_input_mode):
        created["llm_config"] = llm_config
        created["name"] = name
        return _StubAssistant(name=name, system_message=system_message, llm_config=llm_config)

    monkeypatch.setattr(agent_mod, "AssistantAgent", _fake_assistant)

    agent_mod.create_panelist_agent(
        {"name": "ClaudePanel", "provider": "anthropic", "model": "claude-3-5-haiku-20241022"},
        api_key="CLAUDE_KEY",
    )

    cfg = created["llm_config"]["config_list"][0]
    assert cfg["api_type"] == "anthropic"
    assert cfg["api_key"] == "CLAUDE_KEY"
    assert cfg["model"] == "claude-3-5-haiku-20241022"
