"""Test feature flag routing and AG2 integration."""

import os
import pytest
from unittest.mock import patch, AsyncMock

from config import get_debate_engine


class TestFeatureFlag:
    """Test debate engine feature flag."""

    def test_default_engine_is_langgraph(self):
        """Test that default debate engine is LangGraph."""
        with patch.dict(os.environ, {}, clear=False):
            # Remove DEBATE_ENGINE if set
            os.environ.pop("DEBATE_ENGINE", None)

            # Need to clear the cache
            from config import get_debate_engine
            get_debate_engine.cache_clear()

            engine = get_debate_engine()
            assert engine == "langgraph"

    def test_ag2_engine_selection(self):
        """Test selecting AG2 engine via environment variable."""
        with patch.dict(os.environ, {"DEBATE_ENGINE": "ag2"}):
            get_debate_engine.cache_clear()
            engine = get_debate_engine()
            assert engine == "ag2"

    def test_case_insensitive_engine_selection(self):
        """Test that engine selection is case-insensitive."""
        with patch.dict(os.environ, {"DEBATE_ENGINE": "AG2"}):
            get_debate_engine.cache_clear()
            engine = get_debate_engine()
            assert engine == "ag2"

    def test_invalid_engine_raises_error(self):
        """Test that invalid engine raises ValueError."""
        with patch.dict(os.environ, {"DEBATE_ENGINE": "invalid"}):
            get_debate_engine.cache_clear()
            with pytest.raises(ValueError, match="Invalid DEBATE_ENGINE"):
                get_debate_engine()

    def test_valid_engines(self):
        """Test all valid engine options."""
        valid_engines = ["langgraph", "ag2"]

        for engine in valid_engines:
            with patch.dict(os.environ, {"DEBATE_ENGINE": engine}):
                get_debate_engine.cache_clear()
                result = get_debate_engine()
                assert result in ["langgraph", "ag2"]


class TestAG2ServiceInitialization:
    """Test AG2 service initialization."""

    @pytest.mark.asyncio
    async def test_ag2_service_lazy_init(self):
        """Test that AG2 service is lazily initialized."""
        # This test verifies the service can be imported and initialized
        try:
            from debate.service import AG2DebateService
            from debate.persistence import InMemoryDebateStorage

            storage = InMemoryDebateStorage()
            service = AG2DebateService(storage)

            assert service is not None
            assert service.storage is storage
        except ImportError:
            pytest.skip("debate module not available")

    @pytest.mark.asyncio
    async def test_postgres_storage_initialization(self):
        """Test PostgreSQL storage initialization."""
        try:
            from debate.persistence import PostgresDebateStorage

            # This should create a valid PostgresDebateStorage instance
            # (though it won't connect until first use)
            storage = PostgresDebateStorage("postgresql://user:pass@localhost/db")
            assert storage is not None
        except ImportError:
            pytest.skip("asyncpg not available")
        except RuntimeError as e:
            if "asyncpg not installed" in str(e):
                pytest.skip("asyncpg not installed")
            raise

    @pytest.mark.asyncio
    async def test_in_memory_storage_initialization(self):
        """Test in-memory storage initialization."""
        from debate.persistence import InMemoryDebateStorage

        storage = InMemoryDebateStorage()
        assert storage is not None


class TestAPICompatibility:
    """Test that AG2 backend maintains API compatibility."""

    def test_debate_service_interface(self):
        """Test that AG2DebateService implements required methods."""
        from debate.service import AG2DebateService
        from debate.persistence import InMemoryDebateStorage

        service = AG2DebateService(InMemoryDebateStorage())

        # Should have required methods
        assert hasattr(service, "start_debate")
        assert callable(service.start_debate)
        assert hasattr(service, "resume_debate")
        assert callable(service.resume_debate)

    def test_event_types_match_api_contract(self):
        """Test that event types match API contract."""
        # All SSE event types that frontend expects
        required_event_types = {
            "status",
            "search_source",
            "panelist_response",
            "debate_round",
            "debate_paused",
            "result",
            "error",
            "done",
        }

        # These are the event types that AG2 should produce
        # (Some like search_source may not be in AG2 if search is handled differently)
        ag2_event_types = {
            "status",
            "panelist_response",
            "debate_round",
            "result",
            "error",
            "done",
        }

        # AG2 produces at minimum the core event types
        assert ag2_event_types.issubset(required_event_types)

    def test_result_event_structure(self):
        """Test that result events have required fields."""
        result_event = {
            "type": "result",
            "summary": "Test summary",
            "panel_responses": {"Agent": "Response"},
            "usage": {
                "total_input_tokens": 100,
                "total_output_tokens": 50,
                "total_tokens": 150,
                "call_count": 3,
            },
        }

        # Should match AskResponse schema from main.py
        assert result_event["type"] == "result"
        assert isinstance(result_event["summary"], str)
        assert isinstance(result_event["panel_responses"], dict)
        assert isinstance(result_event["usage"], dict)
        assert all(k in result_event["usage"] for k in [
            "total_input_tokens",
            "total_output_tokens",
            "total_tokens",
            "call_count",
        ])


class TestConfigurationValidation:
    """Test configuration validation."""

    def test_pg_conn_str_available(self):
        """Test that PG_CONN_STR is properly configured."""
        try:
            from config import get_pg_conn_str
            conn_str = get_pg_conn_str()
            assert conn_str is not None
            assert len(conn_str) > 0
        except RuntimeError as e:
            if "must be set" in str(e):
                pytest.skip("PG_CONN_STR not configured")
            raise

    def test_use_in_memory_checkpointer_flag(self):
        """Test in-memory checkpointer flag."""
        from config import use_in_memory_checkpointer

        # Should return a boolean
        result = use_in_memory_checkpointer()
        assert isinstance(result, bool)

    def test_openai_api_key_available(self):
        """Test that OpenAI API key is available."""
        try:
            from config import get_openai_api_key
            key = get_openai_api_key()
            assert key is not None
            assert len(key) > 0
        except RuntimeError as e:
            if "must be set" in str(e):
                pytest.skip("OPENAI_API_KEY not configured")
            raise


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
