"""Persistence layer for debate state.

Simple JSON-based storage in PostgreSQL.
No LangGraph checkpointer complexity - just save/load state as JSON.
"""

import json
import logging
from typing import Protocol, Dict, Any

from .state import DebateState

logger = logging.getLogger(__name__)


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

    def __init__(self, db_conn_factory=None):
        """Initialize with optional custom connection factory.

        Args:
            db_conn_factory: Optional async connection factory
                           Defaults to using get_db_connection() from main
        """
        self.db_conn_factory = db_conn_factory

    async def _get_connection(self):
        """Get database connection.

        Uses injected factory or falls back to importing from main.
        """
        if self.db_conn_factory:
            return self.db_conn_factory()

        # Lazy import to avoid circular dependencies
        from main import get_db_connection
        return get_db_connection()

    async def save(self, thread_id: str, state: DebateState) -> None:
        """Save state as JSON to PostgreSQL.

        Args:
            thread_id: Thread identifier
            state: State to save
        """
        raise NotImplementedError("Implement in Phase 3")

    async def load(self, thread_id: str) -> DebateState:
        """Load state from PostgreSQL JSON.

        Args:
            thread_id: Thread identifier

        Returns:
            DebateState

        Raises:
            ValueError: If state not found
        """
        raise NotImplementedError("Implement in Phase 3")


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
