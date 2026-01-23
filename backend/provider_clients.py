"""Helpers for retrieving available models from external providers."""
from __future__ import annotations

import logging
from enum import Enum
from typing import Any, List, TypedDict

import httpx

logger = logging.getLogger(__name__)


class ProviderName(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    CLAUDE = "claude"
    GROK = "grok"


class QuotaStatus(TypedDict):
    available: bool
    error: str | None
    provider: str


class ModelInfo(TypedDict):
    id: str
    label: str


async def fetch_provider_models(provider: ProviderName, api_key: str) -> List[ModelInfo]:
    api_key = api_key.strip()
    if not api_key:
        raise ValueError("API key is required")

    if provider is ProviderName.OPENAI:
        return await _fetch_openai_models(api_key)
    if provider is ProviderName.GEMINI:
        return await _fetch_gemini_models(api_key)
    if provider is ProviderName.CLAUDE:
        return await _fetch_claude_models(api_key)
    if provider is ProviderName.GROK:
        return await _fetch_grok_models(api_key)
    raise ValueError(f"Unsupported provider: {provider}")


async def _fetch_openai_models(api_key: str) -> List[ModelInfo]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get("https://api.openai.com/v1/models", headers=headers)
    data = _decode_response(response, "Failed to load OpenAI models")
    models = data.get("data") if isinstance(data, dict) else []
    entries: List[ModelInfo] = []
    for model in models or []:
        model_id = model.get("id") if isinstance(model, dict) else None
        if isinstance(model_id, str) and ("gpt" in model_id or model_id.startswith("o") or model_id.startswith("ft:")):
            entries.append({"id": model_id, "label": model_id})
    return sorted(entries, key=lambda item: item["id"])


async def _fetch_gemini_models(api_key: str) -> List[ModelInfo]:
    params = {"key": api_key}
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get("https://generativelanguage.googleapis.com/v1/models", params=params)
    data = _decode_response(response, "Failed to load Gemini models")
    models = data.get("models") if isinstance(data, dict) else []
    entries: List[ModelInfo] = []
    for model in models or []:
        if not isinstance(model, dict):
            continue
        name = model.get("name")
        model_id = name.split("/")[-1] if isinstance(name, str) else None
        display = model.get("displayName") if isinstance(model.get("displayName"), str) else None
        if model_id:
            label = display if display else model_id
            if display and display != model_id:
                label = f"{display} ({model_id})"
            entries.append({"id": model_id, "label": label})
    return entries


async def _fetch_claude_models(api_key: str) -> List[ModelInfo]:
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get("https://api.anthropic.com/v1/models", headers=headers)
    data = _decode_response(response, "Failed to load Claude models")
    models = data.get("data") if isinstance(data, dict) else []
    entries: List[ModelInfo] = []
    for model in models or []:
        if not isinstance(model, dict):
            continue
        model_id = model.get("id")
        if isinstance(model_id, str):
            label = model.get("display_name")
            entries.append({"id": model_id, "label": label or model_id})
    return entries


async def _fetch_grok_models(api_key: str) -> List[ModelInfo]:
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get("https://api.x.ai/v1/models", headers=headers)
    data = _decode_response(response, "Failed to load Grok models")
    if isinstance(data, dict):
        models = data.get("data") or data.get("models") or []
    else:
        models = []
    entries: List[ModelInfo] = []
    for model in models or []:
        if not isinstance(model, dict):
            continue
        model_id = model.get("id") or model.get("name")
        label = model.get("name") or model_id
        if isinstance(model_id, str) and isinstance(label, str):
            entries.append({"id": model_id, "label": label})
    return entries


def _decode_response(response: httpx.Response, fallback: str) -> Any:
    try:
        data = response.json()
    except ValueError:
        data = None
    if response.is_success:
        return data or {}
    message = _extract_error_message(data) or response.text or fallback
    raise ValueError(message.strip() or fallback)


def _extract_error_message(payload: Any) -> str | None:
    if isinstance(payload, dict):
        error = payload.get("error")
        if isinstance(error, dict):
            message = error.get("message") or error.get("error")
            if isinstance(message, str):
                return message
        elif isinstance(error, str):
            return error
        message = payload.get("message")
        if isinstance(message, str):
            return message
    return None


# ============================================================================
# Quota / Rate Limit Checking
# ============================================================================


async def check_provider_quota(provider: ProviderName, api_key: str) -> QuotaStatus:
    """Check if a provider's API key has available quota.

    Makes a minimal API call to verify the key works and quota is available.
    Returns status indicating if the provider can be used.
    """
    api_key = api_key.strip()
    if not api_key:
        return {"available": False, "error": "No API key provided", "provider": provider.value}

    try:
        if provider is ProviderName.OPENAI:
            return await _check_openai_quota(api_key)
        if provider is ProviderName.GEMINI:
            return await _check_gemini_quota(api_key)
        if provider is ProviderName.CLAUDE:
            return await _check_claude_quota(api_key)
        if provider is ProviderName.GROK:
            return await _check_grok_quota(api_key)
        return {"available": False, "error": f"Unknown provider: {provider}", "provider": provider.value}
    except Exception as e:
        logger.warning(f"Quota check failed for {provider.value}: {e}")
        return {"available": False, "error": str(e), "provider": provider.value}


async def _check_openai_quota(api_key: str) -> QuotaStatus:
    """Check OpenAI quota by making a minimal completion request."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    # Use a minimal completion to check quota (1 token max)
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
        )

    if response.is_success:
        return {"available": True, "error": None, "provider": "openai"}

    error = _extract_quota_error(response, "openai")
    return {"available": False, "error": error, "provider": "openai"}


async def _check_gemini_quota(api_key: str) -> QuotaStatus:
    """Check Gemini quota by making a minimal generation request."""
    params = {"key": api_key}
    payload = {
        "contents": [{"parts": [{"text": "hi"}]}],
        "generationConfig": {"maxOutputTokens": 1},
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent",
            params=params,
            json=payload,
        )

    if response.is_success:
        return {"available": True, "error": None, "provider": "gemini"}

    error = _extract_quota_error(response, "gemini")
    return {"available": False, "error": error, "provider": "gemini"}


async def _check_claude_quota(api_key: str) -> QuotaStatus:
    """Check Claude quota by making a minimal message request."""
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "claude-3-haiku-20240307",
        "max_tokens": 1,
        "messages": [{"role": "user", "content": "hi"}],
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
        )

    if response.is_success:
        return {"available": True, "error": None, "provider": "claude"}

    error = _extract_quota_error(response, "claude")
    return {"available": False, "error": error, "provider": "claude"}


async def _check_grok_quota(api_key: str) -> QuotaStatus:
    """Check Grok quota by making a minimal completion request."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "grok-2-latest",
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
    }
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers=headers,
            json=payload,
        )

    if response.is_success:
        return {"available": True, "error": None, "provider": "grok"}

    error = _extract_quota_error(response, "grok")
    return {"available": False, "error": error, "provider": "grok"}


def _extract_quota_error(response: httpx.Response, provider: str) -> str:
    """Extract a human-readable error message from API response."""
    try:
        data = response.json()
    except ValueError:
        data = None

    status = response.status_code

    # Common quota/rate limit status codes
    if status == 429:
        msg = _extract_error_message(data) or "Rate limit exceeded"
        return f"Quota exhausted: {msg}"
    if status == 402:
        return "Payment required - billing issue or quota exhausted"
    if status == 401:
        return "Invalid API key"
    if status == 403:
        return "Access denied - check API key permissions"

    # Try to extract specific error message
    msg = _extract_error_message(data)
    if msg:
        # Check for quota-related keywords
        lower_msg = msg.lower()
        if any(kw in lower_msg for kw in ["quota", "limit", "exceeded", "billing", "insufficient"]):
            return f"Quota issue: {msg}"
        return msg

    return f"API error (HTTP {status})"
