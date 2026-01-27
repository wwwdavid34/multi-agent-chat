"""Test configuration validation."""

import os
import pytest
from unittest.mock import patch


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
