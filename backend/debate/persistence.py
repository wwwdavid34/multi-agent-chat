"""Persistence layer for debate state.

Simple JSON-based storage in PostgreSQL.
No LangGraph checkpointer complexity - just save/load state as JSON.
"""

import json
import logging
from typing import Protocol, Dict, Any, Optional

from .state import DebateState

logger = logging.getLogger(__name__)

try:
    import asyncpg
except ImportError:
    asyncpg = None


class DebateStorage(Protocol):
    """Storage interface for debate state.

    Allows different implementations (PostgreSQL, Redis, etc.)
    without tightly coupling the orchestrator.
    """

    async def load(self, thread_id: str) -> DebateState:
        """Load debate state for a thread.

        Args:
            thread_id: Unique thread identifier

        Returns:
            DebateState dict

        Raises:
            ValueError: If state not found
        """
        ...

    async def save(self, thread_id: str, state: DebateState) -> None:
        """Save debate state for a thread.

        Args:
            thread_id: Unique thread identifier
            state: DebateState to persist
        """
        ...


class PostgresDebateStorage:
    """PostgreSQL implementation of DebateStorage.

    Stores state as JSON in a simple debate_state table.
    Simpler than LangGraph checkpointing - no threading hacks.

    Expected table schema:
    CREATE TABLE debate_state (
        thread_id TEXT PRIMARY KEY,
        state JSONB NOT NULL,
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """

    def __init__(self, conn_string: str):
        """Initialize with PostgreSQL connection string.

        Args:
            conn_string: asyncpg connection string
        """
        if asyncpg is None:
            raise RuntimeError("asyncpg not installed. Install with: pip install asyncpg")

        self.conn_string = conn_string
        self._pool: Optional[Any] = None

    async def _get_pool(self):
        """Get or create database connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.conn_string, min_size=1, max_size=5)
            await self._ensure_table()
        return self._pool

    async def _ensure_table(self) -> None:
        """Create debate_state table if it doesn't exist."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS debate_state (
                    thread_id TEXT PRIMARY KEY,
                    state JSONB NOT NULL,
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_debate_state_updated ON debate_state(updated_at);
            """)
            logger.debug("Ensured debate_state table exists")

    async def save(self, thread_id: str, state: DebateState) -> None:
        """Save state as JSON to PostgreSQL.

        Args:
            thread_id: Thread identifier
            state: State to save
        """
        try:
            pool = await self._get_pool()
            state_json = json.dumps(state)

            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO debate_state (thread_id, state, updated_at)
                    VALUES ($1, $2, NOW())
                    ON CONFLICT (thread_id) DO UPDATE
                    SET state = $2, updated_at = NOW()
                """, thread_id, state_json)

            logger.debug(f"Saved debate state for thread {thread_id}")
        except Exception as e:
            logger.error(f"Error saving debate state for {thread_id}: {e}")
            raise

    async def load(self, thread_id: str) -> DebateState:
        """Load state from PostgreSQL JSON.

        Args:
            thread_id: Thread identifier

        Returns:
            DebateState

        Raises:
            ValueError: If state not found
        """
        try:
            pool = await self._get_pool()

            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT state FROM debate_state WHERE thread_id = $1",
                    thread_id
                )

            if not row:
                raise ValueError(f"No debate state found for thread {thread_id}")

            state_data = row["state"]
            # Handle both string and dict (asyncpg may return dict for JSONB)
            if isinstance(state_data, str):
                state = json.loads(state_data)
            else:
                state = state_data

            logger.debug(f"Loaded debate state for thread {thread_id}")
            return state
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error loading debate state for {thread_id}: {e}")
            raise


class InMemoryDebateStorage:
    """In-memory implementation for testing.

    Simple dict-based storage - not for production.
    """

    def __init__(self):
        """Initialize empty storage."""
        self.states: Dict[str, DebateState] = {}

    async def save(self, thread_id: str, state: DebateState) -> None:
        """Save state to memory."""
        self.states[thread_id] = state

    async def load(self, thread_id: str) -> DebateState:
        """Load state from memory."""
        if thread_id not in self.states:
            raise ValueError(f"No state found for thread {thread_id}")
        return self.states[thread_id]
