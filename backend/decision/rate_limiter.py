"""Per-provider token-per-minute (TPM) rate limiter for decision experts.

Uses a sliding-window approach: each provider tracks token usage entries
with timestamps.  Before an LLM call, ``acquire()`` checks if the
rolling 60-second total would exceed the TPM budget and sleeps until
enough headroom exists.  After the call, ``record()`` logs actual usage.

Thread-safe via asyncio.Lock (all expert coroutines share one limiter
within the same event loop).
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

DEFAULT_TPM = 30_000  # tokens per minute per provider

_WINDOW_SECONDS = 60.0
_POLL_INTERVAL = 1.0  # seconds between re-checks when waiting


@dataclass
class _UsageEntry:
    timestamp: float
    tokens: int


@dataclass
class _ProviderBucket:
    entries: list[_UsageEntry] = field(default_factory=list)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def _prune(self, now: float) -> None:
        cutoff = now - _WINDOW_SECONDS
        self.entries = [e for e in self.entries if e.timestamp > cutoff]

    def window_total(self, now: float | None = None) -> int:
        now = now or time.monotonic()
        self._prune(now)
        return sum(e.tokens for e in self.entries)


class ProviderRateLimiter:
    """Singleton-style rate limiter shared across all expert coroutines."""

    def __init__(self, tpm_limit: int = DEFAULT_TPM) -> None:
        self.tpm_limit = tpm_limit
        self._buckets: dict[str, _ProviderBucket] = {}

    def _bucket(self, provider: str) -> _ProviderBucket:
        if provider not in self._buckets:
            self._buckets[provider] = _ProviderBucket()
        return self._buckets[provider]

    async def acquire(self, provider: str, estimated_tokens: int) -> None:
        """Wait until *estimated_tokens* can fit within the provider's TPM window."""
        bucket = self._bucket(provider)
        while True:
            async with bucket.lock:
                now = time.monotonic()
                current = bucket.window_total(now)
                if current + estimated_tokens <= self.tpm_limit:
                    # Reserve the estimate immediately so parallel coroutines
                    # see it and don't all rush in at once.
                    bucket.entries.append(_UsageEntry(timestamp=now, tokens=estimated_tokens))
                    return
                headroom = self.tpm_limit - current
            logger.info(
                "TPM throttle: provider=%s, window=%d/%d, need=%d, headroom=%d — waiting %.1fs",
                provider, current, self.tpm_limit, estimated_tokens, headroom, _POLL_INTERVAL,
            )
            await asyncio.sleep(_POLL_INTERVAL)

    def record(self, provider: str, actual_tokens: int, estimated_tokens: int) -> None:
        """Replace the earlier estimate with actual usage.

        Call this after the LLM response is received.  The difference
        (actual - estimated) is added as a correction entry so the
        window total stays accurate.
        """
        diff = actual_tokens - estimated_tokens
        if diff == 0:
            return
        bucket = self._bucket(provider)
        now = time.monotonic()
        # Add a correction entry (can be negative if we over-estimated)
        bucket.entries.append(_UsageEntry(timestamp=now, tokens=diff))
        logger.debug(
            "TPM record: provider=%s, estimated=%d, actual=%d, correction=%+d, window=%d/%d",
            provider, estimated_tokens, actual_tokens, diff, bucket.window_total(now), self.tpm_limit,
        )


# Module-level singleton — shared by all expert coroutines in the process
_limiter: ProviderRateLimiter | None = None


def get_rate_limiter(tpm_limit: int = DEFAULT_TPM) -> ProviderRateLimiter:
    """Return (or create) the process-wide rate limiter."""
    global _limiter
    if _limiter is None or _limiter.tpm_limit != tpm_limit:
        _limiter = ProviderRateLimiter(tpm_limit=tpm_limit)
    return _limiter
