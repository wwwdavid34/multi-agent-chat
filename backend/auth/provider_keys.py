"""Provider key resolution with BYOK enforcement.

This module handles the logic for determining which API keys to use:
1. Keys from request (BYOK provided by user in this request)
2. User's stored encrypted keys (if authenticated)
3. System keys (only if user is allowlisted for that provider)
"""

import logging
import os
from typing import Dict, Optional, Set
from uuid import UUID

import asyncpg

from auth.encryption import decrypt_api_keys
from auth.models import TokenPayload

logger = logging.getLogger(__name__)

# Provider name mapping (frontend uses different names than env vars)
PROVIDER_ENV_VARS = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "claude": "ANTHROPIC_API_KEY",  # Alias
    "google": "GEMINI_API_KEY",
    "gemini": "GEMINI_API_KEY",  # Alias
    "xai": "XAI_API_KEY",
    "grok": "XAI_API_KEY",  # Alias
}

# Canonical provider names for allowlist
CANONICAL_PROVIDERS = {
    "openai": "openai",
    "anthropic": "anthropic",
    "claude": "anthropic",
    "google": "google",
    "gemini": "google",
    "xai": "xai",
    "grok": "xai",
}


async def get_user_allowlisted_providers(
    email: str,
    pool: asyncpg.Pool,
) -> Set[str]:
    """Get the set of providers a user is allowlisted for."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT provider FROM system_key_allowlist WHERE email = $1",
            email,
        )
        return {row["provider"] for row in rows}


async def get_user_stored_keys(
    user_id: str,
    pool: asyncpg.Pool,
) -> Dict[str, str]:
    """Get user's stored encrypted API keys."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT encrypted_api_keys, encryption_salt FROM users WHERE id = $1",
            UUID(user_id),
        )

        if not row or not row["encrypted_api_keys"] or not row["encryption_salt"]:
            return {}

        try:
            return decrypt_api_keys(
                row["encrypted_api_keys"],
                user_id,
                row["encryption_salt"],
            )
        except Exception as e:
            logger.error(f"Failed to decrypt stored keys for user {user_id}: {e}")
            return {}


def get_system_key(provider: str) -> Optional[str]:
    """Get system API key from environment for a provider."""
    canonical = CANONICAL_PROVIDERS.get(provider.lower(), provider.lower())
    env_var = PROVIDER_ENV_VARS.get(canonical)
    if env_var:
        return os.environ.get(env_var)
    return None


async def resolve_provider_keys(
    request_keys: Optional[Dict[str, str]],
    user: Optional[TokenPayload],
    pool: Optional[asyncpg.Pool],
    required_providers: Optional[Set[str]] = None,
) -> Dict[str, str]:
    """
    Resolve provider keys with BYOK enforcement.

    Priority order:
    1. Keys from request (BYOK in this request)
    2. User's stored encrypted keys (if authenticated)
    3. System keys (only if user is allowlisted)

    Args:
        request_keys: Keys provided in the current request
        user: Authenticated user (or None for anonymous)
        pool: Database connection pool
        required_providers: Set of providers that need keys (for validation)

    Returns:
        Dict of provider -> api_key

    Raises:
        ValueError: If required provider keys are missing
    """
    resolved_keys: Dict[str, str] = {}
    request_keys = request_keys or {}

    # 1. Add keys from request (BYOK)
    for provider, key in request_keys.items():
        if key and key.strip():
            resolved_keys[provider.lower()] = key.strip()
            logger.debug(f"Using BYOK key for {provider}")

    # 2. Add user's stored keys (if authenticated and pool available)
    if user and pool:
        try:
            stored_keys = await get_user_stored_keys(user.user_id, pool)
            for provider, key in stored_keys.items():
                if provider.lower() not in resolved_keys and key:
                    resolved_keys[provider.lower()] = key
                    logger.debug(f"Using stored key for {provider}")
        except Exception as e:
            logger.warning(f"Could not fetch stored keys: {e}")

    # 3. Add system keys for allowlisted users only
    if user and pool:
        try:
            allowlisted = await get_user_allowlisted_providers(user.email, pool)
            for provider in allowlisted:
                canonical = CANONICAL_PROVIDERS.get(provider, provider)
                if canonical not in resolved_keys:
                    system_key = get_system_key(canonical)
                    if system_key:
                        resolved_keys[canonical] = system_key
                        logger.debug(f"Using system key for {provider} (user allowlisted)")
        except Exception as e:
            logger.warning(f"Could not check allowlist: {e}")

    # Validate required providers have keys
    if required_providers:
        missing = []
        for provider in required_providers:
            canonical = CANONICAL_PROVIDERS.get(provider.lower(), provider.lower())
            if canonical not in resolved_keys:
                missing.append(provider)

        if missing:
            if user:
                raise ValueError(
                    f"Missing API keys for: {', '.join(missing)}. "
                    "Please add your own keys or contact an admin for system key access."
                )
            else:
                raise ValueError(
                    f"Missing API keys for: {', '.join(missing)}. "
                    "Please sign in and add your API keys, or provide them in this request."
                )

    return resolved_keys


async def log_system_key_usage(
    user: TokenPayload,
    provider: str,
    thread_id: str,
    pool: asyncpg.Pool,
    metadata: Optional[Dict] = None,
) -> None:
    """Log usage of system keys for audit purposes."""
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO system_key_audit (user_id, user_email, provider, thread_id, action, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                UUID(user.user_id),
                user.email,
                provider,
                thread_id,
                "api_call",
                metadata,
            )
    except Exception as e:
        logger.error(f"Failed to log system key usage: {e}")
