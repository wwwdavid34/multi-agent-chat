"""Application configuration helpers."""
from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import quote, urlparse, urlunparse

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


def _encode_pg_password(conn_str: str) -> str:
    """Encode password in PostgreSQL connection URI if needed.

    Handles passwords with special characters like @, *, <, (, ), etc.
    by properly URL-encoding them.
    """
    # If it's a keyword=value style connection string, return as-is
    if not conn_str.startswith(("postgres://", "postgresql://")):
        return conn_str

    try:
        # Extract scheme and rest
        scheme_end = conn_str.index("://") + 3
        scheme = conn_str[:scheme_end]
        rest = conn_str[scheme_end:]

        # Find the last @ which separates credentials from host
        # (because password might contain @ symbols)
        last_at = rest.rfind("@")

        if last_at == -1:
            # No credentials in URL
            return conn_str

        credentials = rest[:last_at]
        host_part = rest[last_at + 1:]

        # Split credentials into username and password
        if ":" in credentials:
            username, password = credentials.split(":", 1)
            # URL-encode both username and password to handle special chars
            encoded_username = quote(username, safe="")
            encoded_password = quote(password, safe="")
            # Reconstruct the connection string
            return f"{scheme}{encoded_username}:{encoded_password}@{host_part}"
        else:
            # Only username, no password
            encoded_username = quote(credentials, safe="")
            return f"{scheme}{encoded_username}@{host_part}"

    except Exception as e:
        # If parsing fails, log and return the original string
        import logging
        logging.debug(f"Failed to encode postgres password: {e}, using original")
        return conn_str


@lru_cache(maxsize=None)
def get_pg_conn_str() -> str:
    """Return the Postgres connection string with properly encoded password."""
    conn_str = _require_env("PG_CONN_STR")
    return _encode_pg_password(conn_str)


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
def get_tavily_api_key() -> str:
    """Return the Tavily API key for web search."""

    value = _optional_env("TAVILY_API_KEY")
    if not value:
        raise RuntimeError("Set TAVILY_API_KEY to enable web search functionality")
    return value


@lru_cache(maxsize=None)
def use_in_memory_checkpointer() -> bool:
    """Return True when an in-memory LangGraph checkpointer should be used."""

    flag = os.getenv("USE_IN_MEMORY_CHECKPOINTER", "0").lower()
    return flag in {"1", "true", "yes", "on"}


@lru_cache(maxsize=None)
def get_debate_engine() -> str:
    """Get the debate engine to use: 'langgraph' (legacy) or 'ag2' (new).

    Default: 'langgraph' for backward compatibility.
    Set DEBATE_ENGINE=ag2 to use the new AG2 backend.
    """
    engine = os.getenv("DEBATE_ENGINE", "langgraph").lower()
    if engine not in {"langgraph", "ag2"}:
        raise ValueError(f"Invalid DEBATE_ENGINE: {engine}. Must be 'langgraph' or 'ag2'")
    return engine
