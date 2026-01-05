"""Unit tests for AG2 debate backend."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from debate.state import DebateState, DebateRound
from debate.orchestrator import DebateOrchestrator
from debate.persistence import InMemoryDebateStorage
from debate.service import AG2DebateService
from debate.usage import UsageAccumulator, track_usage


class TestUsageTracking:
    """Test usage tracking functionality."""

    def test_track_usage(self):
        """Test extracting usage from agent response."""
        usage = track_usage("TestAgent", "Sample response")

        assert isinstance(usage, dict)
        assert "agent" in usage
        assert "input_tokens" in usage
        assert "output_tokens" in usage
        assert "total_tokens" in usage
        assert usage["agent"] == "TestAgent"

    def test_usage_accumulator(self):
        """Test accumulating usage across calls."""
        accumulator = UsageAccumulator()

        # Add responses from multiple agents
        accumulator.add("Agent1", "Response 1")
        accumulator.add("Agent2", "Response 2")
        accumulator.add("Agent3", "Response 3")

        # Summarize should return proper format
        summary = accumulator.summarize()
        assert summary["call_count"] == 3
        assert "total_input_tokens" in summary
        assert "total_output_tokens" in summary
        assert "total_tokens" in summary

    def test_usage_accumulator_reset(self):
        """Test resetting usage accumulator."""
        accumulator = UsageAccumulator()
        accumulator.add("Agent1", "Response")

        assert accumulator.summarize()["call_count"] == 1

        accumulator.reset()
        assert accumulator.summarize()["call_count"] == 0


class TestDebateState:
    """Test debate state initialization and transitions."""

    def test_initial_debate_state(self):
        """Test creating initial debate state."""
        state: DebateState = {
            "thread_id": "test-thread",
            "phase": "init",
            "debate_round": 0,
            "max_rounds": 3,
            "consensus_reached": False,
            "debate_mode": True,
            "user_as_participant": False,
            "tagged_panelists": [],
            "panelists": [],
            "question": "Test question",
            "summary": None,
            "panel_responses": {},
            "debate_history": [],
        }

        assert state["phase"] == "init"
        assert state["debate_round"] == 0
        assert state["max_rounds"] == 3
        assert len(state["panel_responses"]) == 0

    def test_debate_round_structure(self):
        """Test DebateRound structure."""
        round_data: DebateRound = {
            "round_number": 1,
            "panel_responses": {
                "Agent1": "Response 1",
                "Agent2": "Response 2",
            },
            "consensus_reached": False,
            "user_message": None,
        }

        assert round_data["round_number"] == 1
        assert len(round_data["panel_responses"]) == 2
        assert round_data["consensus_reached"] is False


class TestInMemoryStorage:
    """Test in-memory storage implementation."""

    @pytest.mark.asyncio
    async def test_save_and_load_state(self):
        """Test saving and loading debate state."""
        storage = InMemoryDebateStorage()

        state: DebateState = {
            "thread_id": "test-thread",
            "phase": "debate",
            "debate_round": 1,
            "max_rounds": 3,
            "consensus_reached": False,
            "debate_mode": True,
            "user_as_participant": False,
            "tagged_panelists": [],
            "panelists": [],
            "question": "Test",
            "summary": None,
            "panel_responses": {"Agent": "Response"},
            "debate_history": [],
        }

        # Save state
        await storage.save("test-thread", state)

        # Load state
        loaded = await storage.load("test-thread")
        assert loaded["thread_id"] == "test-thread"
        assert loaded["phase"] == "debate"
        assert loaded["debate_round"] == 1

    @pytest.mark.asyncio
    async def test_load_nonexistent_state(self):
        """Test loading non-existent state raises error."""
        storage = InMemoryDebateStorage()

        with pytest.raises(ValueError, match="No state found"):
            await storage.load("nonexistent")


class TestAG2DebateService:
    """Test AG2 debate service."""

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test initializing debate service."""
        storage = InMemoryDebateStorage()
        service = AG2DebateService(storage)

        assert service.storage is not None
        assert service.storage is storage

    @pytest.mark.asyncio
    async def test_start_debate_creates_state(self):
        """Test that start_debate initializes proper state."""
        storage = InMemoryDebateStorage()
        service = AG2DebateService(storage)

        # We can't fully test start_debate without AG2 installed,
        # but we can verify it's callable
        assert hasattr(service, 'start_debate')
        assert callable(service.start_debate)

    @pytest.mark.asyncio
    async def test_resume_debate_requires_paused_state(self):
        """Test that resume_debate validates state."""
        storage = InMemoryDebateStorage()
        service = AG2DebateService(storage)

        # Save a non-paused state
        state: DebateState = {
            "thread_id": "test",
            "phase": "debate",  # Not paused
            "debate_round": 1,
            "max_rounds": 3,
            "consensus_reached": False,
            "debate_mode": True,
            "user_as_participant": False,
            "tagged_panelists": [],
            "panelists": [],
            "question": "Test",
            "summary": None,
            "panel_responses": {},
            "debate_history": [],
        }
        await storage.save("test", state)

        # Try to resume - should fail
        events = []
        async for event in service.resume_debate("test"):
            events.append(event)

        # Should get error event
        assert any(e.get("type") == "error" for e in events)


class TestOrchestrator:
    """Test DebateOrchestrator phase transitions."""

    @pytest.mark.asyncio
    async def test_phase_init_to_debate(self):
        """Test phase transition from init to debate."""
        queue = asyncio.Queue()
        state: DebateState = {
            "thread_id": "test",
            "phase": "init",
            "debate_round": 0,
            "max_rounds": 1,
            "consensus_reached": False,
            "debate_mode": False,
            "user_as_participant": False,
            "tagged_panelists": [],
            "panelists": [],
            "question": "Test",
            "summary": None,
            "panel_responses": {},
            "debate_history": [],
        }

        orchestrator = DebateOrchestrator(state, queue)

        # Mock the initialize method to avoid AG2 dependency
        orchestrator.initialize = AsyncMock()

        await orchestrator.step()

        # Should transition from init to debate
        assert state["phase"] == "debate"
        orchestrator.initialize.assert_called_once()

    def test_phase_machine_states(self):
        """Test that valid phase transitions are possible."""
        valid_states = {"init", "debate", "paused", "moderation", "finished"}

        # Create a minimal state
        state: DebateState = {
            "thread_id": "test",
            "phase": "init",
            "debate_round": 0,
            "max_rounds": 3,
            "consensus_reached": False,
            "debate_mode": False,
            "user_as_participant": False,
            "tagged_panelists": [],
            "panelists": [],
            "question": "Test",
            "summary": None,
            "panel_responses": {},
            "debate_history": [],
        }

        # All states should be in valid_states
        for phase in valid_states:
            state["phase"] = phase
            assert state["phase"] in valid_states


class TestEventQueue:
    """Test event queueing for SSE streaming."""

    @pytest.mark.asyncio
    async def test_event_queue_operations(self):
        """Test basic event queue operations."""
        queue: asyncio.Queue = asyncio.Queue()

        # Put events
        test_events = [
            {"type": "status", "message": "Starting"},
            {"type": "panelist_response", "panelist": "Agent1", "response": "Hello"},
            {"type": "done"},
        ]

        for event in test_events:
            await queue.put(event)

        # Get events
        retrieved = []
        for _ in range(len(test_events)):
            retrieved.append(queue.get_nowait())

        assert len(retrieved) == len(test_events)
        assert retrieved[0]["type"] == "status"
        assert retrieved[1]["type"] == "panelist_response"
        assert retrieved[2]["type"] == "done"


class TestDebateEventTypes:
    """Test proper event type structure."""

    def test_status_event(self):
        """Test status event structure."""
        event = {"type": "status", "message": "Starting panel..."}
        assert event["type"] == "status"
        assert "message" in event

    def test_panelist_response_event(self):
        """Test panelist response event structure."""
        event = {
            "type": "panelist_response",
            "panelist": "Claude",
            "response": "This is my response",
        }
        assert event["type"] == "panelist_response"
        assert "panelist" in event
        assert "response" in event

    def test_debate_round_event(self):
        """Test debate round event structure."""
        round_data: DebateRound = {
            "round_number": 1,
            "panel_responses": {"Agent1": "Response"},
            "consensus_reached": False,
            "user_message": None,
        }
        event = {"type": "debate_round", "round": round_data}
        assert event["type"] == "debate_round"
        assert "round" in event
        assert event["round"]["round_number"] == 1

    def test_result_event(self):
        """Test result event structure."""
        event = {
            "type": "result",
            "summary": "Final summary",
            "panel_responses": {"Agent1": "Response"},
            "usage": {
                "total_input_tokens": 100,
                "total_output_tokens": 50,
                "total_tokens": 150,
                "call_count": 3,
            },
        }
        assert event["type"] == "result"
        assert "summary" in event
        assert "usage" in event
        assert event["usage"]["total_tokens"] == 150

    def test_error_event(self):
        """Test error event structure."""
        event = {"type": "error", "message": "Something went wrong"}
        assert event["type"] == "error"
        assert "message" in event

    def test_done_event(self):
        """Test done event structure."""
        event = {"type": "done"}
        assert event["type"] == "done"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


class TestPanelistFailureValidation:
    """Test that moderator doesn't answer when panelists fail."""

    def test_has_valid_responses_detects_errors(self):
        """Test _has_valid_responses correctly identifies error messages."""
        event_queue = asyncio.Queue()
        state: DebateState = {
            "thread_id": "test",
            "phase": "init",
            "debate_round": 0,
            "max_rounds": 3,
            "consensus_reached": False,
            "panelists": [],
            "debate_mode": True,
            "user_as_participant": False,
            "tagged_panelists": [],
        }
        orchestrator = DebateOrchestrator(state, event_queue)

        # All error responses
        error_responses = {
            "GPT-4": "(Model error: Check model name and API access)",
            "Claude": "(API authentication error: Check API key)",
        }
        assert not orchestrator._has_valid_responses(error_responses)

        # Mix of valid and error
        mixed_responses = {
            "GPT-4": "This is a valid response",
            "Claude": "(API error)",
        }
        assert orchestrator._has_valid_responses(mixed_responses)

        # All valid responses
        valid_responses = {
            "GPT-4": "Valid response from GPT-4",
            "Claude": "Valid response from Claude",
        }
        assert orchestrator._has_valid_responses(valid_responses)

        # Empty responses
        empty_responses: dict = {}
        assert not orchestrator._has_valid_responses(empty_responses)

        # Whitespace-only responses
        whitespace_responses = {
            "GPT-4": "   ",
            "Claude": "\n\t",
        }
        assert not orchestrator._has_valid_responses(whitespace_responses)

    @pytest.mark.asyncio
    async def test_consensus_false_for_error_responses(self):
        """Test consensus returns False when all responses are errors."""
        event_queue = asyncio.Queue()
        state: DebateState = {
            "thread_id": "test",
            "phase": "init",
            "debate_round": 0,
            "max_rounds": 3,
            "consensus_reached": False,
            "panelists": [
                {"id": "gpt", "name": "GPT-4", "provider": "openai", "model": "gpt-4o-mini"},
                {"id": "claude", "name": "Claude", "provider": "anthropic", "model": "claude-3-5-haiku-20241022"},
            ],
            "debate_mode": True,
            "user_as_participant": False,
            "tagged_panelists": [],
        }
        orchestrator = DebateOrchestrator(state, event_queue)

        # Mock the moderator to avoid real API calls
        orchestrator.moderator = MagicMock()

        error_responses = {
            "GPT-4": "(Model error: Check model name and API access)",
            "Claude": "(API authentication error: Check API key)",
        }

        # Should return False without calling moderator
        consensus = await orchestrator._check_consensus(error_responses)
        assert consensus is False
        # Moderator should not be called since we detected no valid responses
        orchestrator.moderator.generate_reply.assert_not_called()
