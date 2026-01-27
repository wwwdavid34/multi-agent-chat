"""Tests for the expert agent tools (search + calculator)."""

from __future__ import annotations

import pytest

from decision.tools.search import create_search_tool
from decision.tools.calculator import create_calculator_tool


# ---------------------------------------------------------------------------
# Search tool
# ---------------------------------------------------------------------------


class TestSearchTool:
    """Verify the web_search tool's metadata."""

    def test_search_tool_has_correct_name(self):
        tool = create_search_tool()
        assert tool.name == "web_search"


# ---------------------------------------------------------------------------
# Calculator tool
# ---------------------------------------------------------------------------


class TestCalculatorTool:
    """Verify the calculator tool's metadata and evaluation logic."""

    def test_calculator_tool_has_correct_name(self):
        tool = create_calculator_tool()
        assert tool.name == "calculator"

    def test_simple_addition(self):
        tool = create_calculator_tool()
        result = tool.invoke("2 + 2")
        assert "= 4" in result

    def test_compound_expression(self):
        tool = create_calculator_tool()
        result = tool.invoke("500000 * 1.05 ** 5")
        # Expected: 500000 * 1.05^5 = 638140.78125
        assert "638140" in result

    def test_rejects_dangerous_code(self):
        tool = create_calculator_tool()
        result = tool.invoke("__import__('os').system('ls')")
        assert "Error" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
