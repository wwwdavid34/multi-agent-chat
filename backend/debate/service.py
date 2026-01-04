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
from .usage import UsageAccumulator

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
        """Start new debate and stream SSE events.

        Initializes debate state, creates orchestrator, and runs debate loop
        while streaming events to frontend.

        Args:
            thread_id: Unique thread identifier
            question: Debate question/topic
            panelists: List of panelist configurations
            **config: Additional config (debate_mode, max_rounds, step_review, etc.)

        Yields:
            SSE event dicts with 'type' field
        """
        event_queue: asyncio.Queue = asyncio.Queue()
        usage_tracker = UsageAccumulator()

        # Initialize debate state
        state: DebateState = {
            "thread_id": thread_id,
            "phase": "init",
            "debate_round": 0,
            "max_rounds": config.get("max_debate_rounds", 3),
            "consensus_reached": False,
            "debate_mode": config.get("debate_mode", False),
            "user_as_participant": config.get("user_as_participant", False),
            "tagged_panelists": config.get("tagged_panelists", []),
            "panelists": panelists,
            "question": question,
            "summary": None,
            "panel_responses": {},
            "debate_history": [],
        }

        # Create orchestrator with event queue
        orchestrator = DebateOrchestrator(state, event_queue)

        # Run debate loop in background task
        async def debate_loop():
            try:
                # Execute debate phases until finished
                while state["phase"] != "finished":
                    # Run one phase step
                    await orchestrator.step()

                    # Save state after each step
                    await self.storage.save(thread_id, state)

                    # If paused, break and wait for resume
                    if state["phase"] == "paused":
                        logger.debug(f"Debate paused for thread {thread_id}")
                        break

                # Emit result event when finished
                if state["phase"] == "finished":
                    result_event = {
                        "type": "result",
                        "summary": state.get("summary", ""),
                        "panel_responses": state.get("panel_responses", {}),
                        "usage": usage_tracker.summarize(),
                    }
                    await event_queue.put(result_event)

            except Exception as e:
                logger.error(f"Error in debate loop: {e}")
                await event_queue.put({
                    "type": "error",
                    "message": str(e),
                })
            finally:
                await event_queue.put({"type": "done"})

        # Start debate loop as background task
        debate_task = asyncio.create_task(debate_loop())

        try:
            # Stream events from queue to frontend
            while True:
                try:
                    event = await asyncio.wait_for(event_queue.get(), timeout=60)

                    # Track usage if response event
                    if event.get("type") == "panelist_response":
                        usage_tracker.add(
                            event.get("panelist", "Unknown"),
                            event.get("response", ""),
                        )

                    yield event

                    # Break on terminal events
                    if event.get("type") in ("done", "error"):
                        break

                except asyncio.TimeoutError:
                    logger.warning(f"Debate event queue timeout for thread {thread_id}")
                    yield {"type": "error", "message": "Debate timeout"}
                    break

        except Exception as e:
            logger.error(f"Error streaming debate events: {e}")
            yield {"type": "error", "message": str(e)}

        finally:
            # Wait for debate task to complete
            if not debate_task.done():
                await debate_task

    async def resume_debate(
        self,
        thread_id: str,
        user_message: Optional[str] = None,
    ) -> AsyncIterator[Dict[str, Any]]:
        """Resume a paused debate.

        Loads state, transitions from paused → debate, and continues the debate loop.

        Args:
            thread_id: Thread identifier
            user_message: Optional message from user

        Yields:
            SSE event dicts continuing from pause point
        """
        event_queue: asyncio.Queue = asyncio.Queue()
        usage_tracker = UsageAccumulator()

        try:
            # Load state from storage
            state = await self.storage.load(thread_id)

            if state.get("phase") != "paused":
                raise ValueError(f"Debate is not paused (phase: {state.get('phase')})")

            # Transition back to debate phase
            state["phase"] = "debate"

            # Store user message if provided
            if user_message:
                state["user_message"] = user_message

            logger.info(f"Resuming debate for thread {thread_id}")

            # Create orchestrator
            orchestrator = DebateOrchestrator(state, event_queue)

            # Run debate loop in background
            async def resume_loop():
                try:
                    # Continue debate from paused state
                    while state["phase"] != "finished":
                        await orchestrator.step()
                        await self.storage.save(thread_id, state)

                        if state["phase"] == "paused":
                            break

                    # Emit result when finished
                    if state["phase"] == "finished":
                        result_event = {
                            "type": "result",
                            "summary": state.get("summary", ""),
                            "panel_responses": state.get("panel_responses", {}),
                            "usage": usage_tracker.summarize(),
                        }
                        await event_queue.put(result_event)

                except Exception as e:
                    logger.error(f"Error resuming debate: {e}")
                    await event_queue.put({
                        "type": "error",
                        "message": str(e),
                    })
                finally:
                    await event_queue.put({"type": "done"})

            # Start resume loop
            resume_task = asyncio.create_task(resume_loop())

            try:
                # Stream events
                while True:
                    try:
                        event = await asyncio.wait_for(event_queue.get(), timeout=60)

                        # Track usage
                        if event.get("type") == "panelist_response":
                            usage_tracker.add(
                                event.get("panelist", "Unknown"),
                                event.get("response", ""),
                            )

                        yield event

                        if event.get("type") in ("done", "error"):
                            break

                    except asyncio.TimeoutError:
                        logger.warning(f"Resume event queue timeout for {thread_id}")
                        yield {"type": "error", "message": "Resume timeout"}
                        break

            finally:
                if not resume_task.done():
                    await resume_task

        except ValueError as e:
            yield {"type": "error", "message": str(e)}
            yield {"type": "done"}
        except Exception as e:
            logger.error(f"Error in resume_debate: {e}")
            yield {"type": "error", "message": str(e)}
            yield {"type": "done"}
