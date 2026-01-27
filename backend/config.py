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


# ============================================================================
# Authentication Configuration
# ============================================================================


@lru_cache(maxsize=None)
def get_google_client_id() -> str:
    """Get Google OAuth client ID.

    Required for Google OAuth authentication.
    Get this from Google Cloud Console > APIs & Services > Credentials.
    """
    client_id = _optional_env("GOOGLE_CLIENT_ID")
    if not client_id:
        raise RuntimeError(
            "GOOGLE_CLIENT_ID environment variable not set. "
            "See GOOGLE_OAUTH_SETUP.md for setup instructions."
        )
    return client_id


@lru_cache(maxsize=None)
def get_jwt_secret_key() -> str:
    """Get JWT secret key for token signing.

    Generate with: openssl rand -hex 32
    """
    secret = _optional_env("JWT_SECRET_KEY")
    if not secret:
        raise RuntimeError(
            "JWT_SECRET_KEY environment variable not set. "
            "Generate one with: openssl rand -hex 32"
        )
    if len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET_KEY is too short (minimum 32 characters). "
            "Generate a new one with: openssl rand -hex 32"
        )
    return secret


@lru_cache(maxsize=None)
def get_encryption_master_key() -> str:
    """Get encryption master key for API key storage.

    Generate with: python -c 'import os, base64; print(base64.b64encode(os.urandom(32)).decode())'
    """
    key = _optional_env("ENCRYPTION_MASTER_KEY")
    if not key:
        raise RuntimeError(
            "ENCRYPTION_MASTER_KEY environment variable not set. "
            "Generate one with: python -c 'import os, base64; "
            "print(base64.b64encode(os.urandom(32)).decode())'"
        )
    return key


@lru_cache(maxsize=None)
def get_frontend_url() -> str:
    """Get frontend URL for CORS configuration.

    Default: http://localhost:5173 for development
    Production: https://chat.yourdomain.com
    """
    return os.getenv("FRONTEND_URL", "http://localhost:5173")


def is_auth_enabled() -> bool:
    """Check if authentication is fully configured.

    Returns True if all required auth environment variables are set.
    """
    try:
        get_google_client_id()
        get_jwt_secret_key()
        get_encryption_master_key()
        return True
    except RuntimeError:
        return False
