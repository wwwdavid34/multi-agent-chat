#!/usr/bin/env python3
"""
Test script for the moderator-driven web search integration.
This script tests the search decision and execution flow.
"""

import asyncio
import os
from langchain_core.messages import HumanMessage
from panel_graph import panel_graph, PanelState


async def test_search_flow():
    """Test the search integration with a question that should trigger search."""

    # Test 1: Question that should trigger search (current event)
    print("=" * 80)
    print("TEST 1: Question that should trigger web search")
    print("=" * 80)

    test_question = "What is the current weather in San Francisco?"

    config = {
        "configurable": {
            "thread_id": "test-search-thread",
            "panelists": [
                {"name": "Weather Expert", "provider": "openai", "model": "gpt-4o-mini"}
            ],
            "provider_keys": {}
        }
    }

    initial_state: PanelState = {
        "messages": [HumanMessage(content=test_question)],
        "panel_responses": {},
        "summary": None,
        "conversation_summary": "",
        "search_results": None,
        "needs_search": False,
    }

    print(f"\nQuestion: {test_question}\n")

    try:
        # Invoke the graph
        result = await panel_graph.ainvoke(initial_state, config)

        print(f"Moderator decided search needed: {result.get('needs_search', False)}")
        print(f"Search results available: {bool(result.get('search_results'))}")

        if result.get('search_results'):
            print(f"\nSearch results preview (first 500 chars):")
            print(result['search_results'][:500] + "...")

        print(f"\nFinal summary:")
        print(result.get('summary', 'No summary generated'))

        print("\n✅ Test 1 PASSED: Search flow executed successfully")

    except Exception as e:
        print(f"\n❌ Test 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Question that should NOT trigger search (general knowledge)
    print("\n\n" + "=" * 80)
    print("TEST 2: Question that should NOT trigger web search")
    print("=" * 80)

    test_question_2 = "What is the capital of France?"

    initial_state_2: PanelState = {
        "messages": [HumanMessage(content=test_question_2)],
        "panel_responses": {},
        "summary": None,
        "conversation_summary": "",
        "search_results": None,
        "needs_search": False,
    }

    print(f"\nQuestion: {test_question_2}\n")

    try:
        result_2 = await panel_graph.ainvoke(initial_state_2, config)

        print(f"Moderator decided search needed: {result_2.get('needs_search', False)}")
        print(f"Search results available: {bool(result_2.get('search_results'))}")

        print(f"\nFinal summary:")
        print(result_2.get('summary', 'No summary generated'))

        print("\n✅ Test 2 PASSED: No-search flow executed successfully")

    except Exception as e:
        print(f"\n❌ Test 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def main():
    """Main test runner."""
    print("\nMODERATOR-DRIVEN WEB SEARCH INTEGRATION TEST")
    print("=" * 80)

    # Check for TAVILY_API_KEY
    if not os.getenv("TAVILY_API_KEY"):
        print("\n⚠️  WARNING: TAVILY_API_KEY not set in environment")
        print("   Search functionality will fail gracefully and use general knowledge")
        print("   To test full search integration, set TAVILY_API_KEY in your .env file\n")

    success = await test_search_flow()

    print("\n" + "=" * 80)
    if success:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
