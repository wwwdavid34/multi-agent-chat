"""Application configuration helpers."""
from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv

# Load variables from .env into process environment as early as possible.
load_dotenv()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} must be set")
    return value


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    return value or None


@lru_cache(maxsize=None)
def get_pg_conn_str() -> str:
    """Return the Postgres connection string, raising if missing."""
    return _require_env("PG_CONN_STR")


@lru_cache(maxsize=None)
def get_openai_api_key() -> str:
    """Ensure the OpenAI API key is configured and return it."""
    return _require_env("OPENAI_API_KEY")


@lru_cache(maxsize=None)
def get_gemini_api_key() -> str:
    """Return the Gemini (Google AI Studio) API key."""

    value = _optional_env("GEMINI_API_KEY")
    if not value:
        raise RuntimeError("Set GEMINI_API_KEY to use the Gemini provider")
    return value


@lru_cache(maxsize=None)
def get_claude_api_key() -> str:
    """Return the Anthropic Claude API key."""

    value = _optional_env("CLAUDE_API_KEY") or _optional_env("ANTHROPIC_API_KEY")
    if not value:
        raise RuntimeError("Set CLAUDE_API_KEY (or ANTHROPIC_API_KEY) to use the Claude provider")
    return value


@lru_cache(maxsize=None)
def get_grok_api_key() -> str:
    """Return the xAI Grok API key."""

    value = _optional_env("GROK_API_KEY") or _optional_env("XAI_API_KEY")
    if not value:
        raise RuntimeError("Set GROK_API_KEY (or XAI_API_KEY) to use the Grok provider")
    return value


@lru_cache(maxsize=None)
def use_in_memory_checkpointer() -> bool:
    """Return True when an in-memory LangGraph checkpointer should be used."""

    flag = os.getenv("USE_IN_MEMORY_CHECKPOINTER", "0").lower()
    return flag in {"1", "true", "yes", "on"}
