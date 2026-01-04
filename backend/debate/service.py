"""Debate service interface and AG2 implementation.

Frozen interface for API contract - no breaking changes allowed.
AG2DebateService provides the implementation using AG2 backend.
"""

import asyncio
import logging
from typing import Protocol, Dict, AsyncIterator, List, Optional, Any

from .state import DebateState, DebateResult
from .orchestrator import DebateOrchestrator
from .persistence import DebateStorage

logger = logging.getLogger(__name__)


class DebateService(Protocol):
    """Frozen service interface for debate orchestration.

    Any implementation must preserve this contract for API compatibility.
    """

    async def start_debate(
        self,
        thread_id: str,
        question: str,
        panelists: List[Dict[str, Any]],
        **config,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Start a new debate and stream SSE events.

        Yields events in order:
        1. status events
        2. panelist_response events
        3. debate_round events
        4. Either debate_paused OR result event
        5. done event

        Args:
            thread_id: Unique identifier for conversation
            question: The question/topic for debate
            panelists: List of PanelistConfig dicts
            **config: debate_mode, max_debate_rounds, step_review, etc.

        Yields:
            SSE events as dicts with "type" field
        """
        ...

    async def resume_debate(
        self,
        thread_id: str,
        user_message: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Resume a paused debate.

        Args:
            thread_id: Identifier of paused debate
            user_message: Optional message from user

        Yields:
            SSE events resuming from pause point
        """
        ...


class AG2DebateService:
    """AG2-based debate service implementation.

    Orchestrates debates using AG2 agents while maintaining
    100% API compatibility with existing frontend.
    """

    def __init__(self, storage: DebateStorage):
        """Initialize service with persistence backend.

        Args:
            storage: DebateStorage implementation (e.g., PostgreSQL)
        """
        self.storage = storage

    async def start_debate(
        self,
        thread_id: str,
        question: str,
        panelists: List[Dict[str, Any]],
        **config,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Start new debate - placeholder implementation.

        Will be implemented in Phase 3.
        """
        raise NotImplementedError("Implement in Phase 3")

    async def resume_debate(
        self,
        thread_id: str,
        user_message: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Resume paused debate - placeholder implementation.

        Will be implemented in Phase 3.
        """
        raise NotImplementedError("Implement in Phase 3")
