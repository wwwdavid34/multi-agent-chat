"""Token usage tracking with PostgreSQL persistence and in-memory fallback."""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TokenUsage:
    """Token usage for a single LLM call."""
    input_tokens: int = 0
    output_tokens: int = 0
    model: str = ""
    provider: str = ""
    node_name: str = ""

    def to_dict(self) -> dict:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "model": self.model,
            "provider": self.provider,
            "node_name": self.node_name,
        }


@dataclass
class RequestUsage:
    """Accumulated token usage for an entire request (Q&A exchange)."""
    thread_id: str
    message_id: str
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    call_details: List[TokenUsage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def add_usage(self, usage: TokenUsage) -> None:
        """Add a single LLM call's usage to the accumulator."""
        self.total_input_tokens += usage.input_tokens
        self.total_output_tokens += usage.output_tokens
        self.call_details.append(usage)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "thread_id": self.thread_id,
            "message_id": self.message_id,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "call_count": len(self.call_details),
        }


class UsageStore:
    """Abstract base for usage storage."""

    async def save(self, usage: RequestUsage) -> None:
        raise NotImplementedError

    async def get_by_thread(self, thread_id: str) -> List[RequestUsage]:
        raise NotImplementedError

    async def get_by_message(self, thread_id: str, message_id: str) -> Optional[RequestUsage]:
        raise NotImplementedError


class InMemoryUsageStore(UsageStore):
    """In-memory fallback storage for usage data."""

    def __init__(self):
        self._storage: Dict[str, Dict[str, RequestUsage]] = {}  # thread_id -> message_id -> usage
        self._lock = asyncio.Lock()

    async def save(self, usage: RequestUsage) -> None:
        async with self._lock:
            if usage.thread_id not in self._storage:
                self._storage[usage.thread_id] = {}
            self._storage[usage.thread_id][usage.message_id] = usage
            logger.debug(f"Saved usage to memory: {usage.thread_id}/{usage.message_id}")

    async def get_by_thread(self, thread_id: str) -> List[RequestUsage]:
        async with self._lock:
            thread_data = self._storage.get(thread_id, {})
            return list(thread_data.values())

    async def get_by_message(self, thread_id: str, message_id: str) -> Optional[RequestUsage]:
        async with self._lock:
            thread_data = self._storage.get(thread_id, {})
            return thread_data.get(message_id)


class PostgresUsageStore(UsageStore):
    """PostgreSQL storage for usage data."""

    def __init__(self, conn_string: str):
        self.conn_string = conn_string
        self._pool = None

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg
            self._pool = await asyncpg.create_pool(self.conn_string, min_size=1, max_size=5)
            await self._ensure_table()
        return self._pool

    async def _ensure_table(self) -> None:
        """Create the usage table if it doesn't exist."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS token_usage (
                    id SERIAL PRIMARY KEY,
                    thread_id VARCHAR(255) NOT NULL,
                    message_id VARCHAR(255) NOT NULL,
                    total_input_tokens INTEGER NOT NULL DEFAULT 0,
                    total_output_tokens INTEGER NOT NULL DEFAULT 0,
                    call_details JSONB,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(thread_id, message_id)
                );
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_usage_thread ON token_usage(thread_id);
            """)

    async def save(self, usage: RequestUsage) -> None:
        pool = await self._get_pool()
        call_details_json = json.dumps([u.to_dict() for u in usage.call_details])
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO token_usage (thread_id, message_id, total_input_tokens, total_output_tokens, call_details)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (thread_id, message_id)
                DO UPDATE SET
                    total_input_tokens = $3,
                    total_output_tokens = $4,
                    call_details = $5
            """, usage.thread_id, usage.message_id, usage.total_input_tokens,
                usage.total_output_tokens, call_details_json)
            logger.debug(f"Saved usage to PostgreSQL: {usage.thread_id}/{usage.message_id}")

    async def get_by_thread(self, thread_id: str) -> List[RequestUsage]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM token_usage WHERE thread_id = $1 ORDER BY created_at",
                thread_id
            )
            return [self._row_to_usage(row) for row in rows]

    async def get_by_message(self, thread_id: str, message_id: str) -> Optional[RequestUsage]:
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM token_usage WHERE thread_id = $1 AND message_id = $2",
                thread_id, message_id
            )
            return self._row_to_usage(row) if row else None

    def _row_to_usage(self, row) -> RequestUsage:
        usage = RequestUsage(
            thread_id=row["thread_id"],
            message_id=row["message_id"],
            total_input_tokens=row["total_input_tokens"],
            total_output_tokens=row["total_output_tokens"],
        )
        if row["call_details"]:
            details = json.loads(row["call_details"]) if isinstance(row["call_details"], str) else row["call_details"]
            for d in details:
                usage.call_details.append(TokenUsage(**d))
        return usage


# Global usage store instance
_usage_store: Optional[UsageStore] = None


async def get_usage_store() -> UsageStore:
    """Get the appropriate usage store (PostgreSQL or in-memory fallback)."""
    global _usage_store
    if _usage_store is not None:
        return _usage_store

    from config import get_pg_conn_str, use_in_memory_checkpointer

    if use_in_memory_checkpointer():
        logger.info("Using in-memory usage store")
        _usage_store = InMemoryUsageStore()
    else:
        try:
            conn_str = get_pg_conn_str()
            store = PostgresUsageStore(conn_str)
            await store._ensure_table()
            _usage_store = store
            logger.info("Using PostgreSQL usage store")
        except Exception as e:
            logger.warning(f"Failed to initialize PostgreSQL usage store, falling back to memory: {e}")
            _usage_store = InMemoryUsageStore()

    return _usage_store


def extract_usage_from_response(response: Any, model: str, provider: str, node_name: str) -> TokenUsage:
    """Extract token usage from an LLM response object.

    Works with LangChain models (ChatOpenAI, ChatAnthropic, ChatGoogleGenerativeAI)
    which attach usage_metadata to AIMessage responses.
    """
    usage = TokenUsage(model=model, provider=provider, node_name=node_name)

    # LangChain models attach usage_metadata to AIMessage
    if hasattr(response, 'usage_metadata') and response.usage_metadata:
        metadata = response.usage_metadata
        usage.input_tokens = metadata.get('input_tokens', 0)
        usage.output_tokens = metadata.get('output_tokens', 0)

    return usage


def create_usage_accumulator() -> Dict[str, Any]:
    """Create a fresh usage accumulator dict."""
    return {
        "calls": [],
        "total_input": 0,
        "total_output": 0,
    }


def add_to_accumulator(
    accumulator: Dict[str, Any],
    response: Any,
    model: str,
    provider: str,
    node_name: str,
    panelist_name: Optional[str] = None
) -> None:
    """Add usage from an LLM response to the accumulator."""
    if hasattr(response, 'usage_metadata') and response.usage_metadata:
        metadata = response.usage_metadata
        input_tokens = metadata.get('input_tokens', 0)
        output_tokens = metadata.get('output_tokens', 0)

        call_info = {
            "node": node_name,
            "model": model,
            "provider": provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
        }
        if panelist_name:
            call_info["panelist_name"] = panelist_name

        accumulator["calls"].append(call_info)
        accumulator["total_input"] += input_tokens
        accumulator["total_output"] += output_tokens
