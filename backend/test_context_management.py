#!/usr/bin/env python3
"""
Test context window management and automatic truncation.
"""

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from panel_graph import _truncate_messages


def test_truncate_messages():
    """Test message truncation logic."""

    print("=" * 80)
    print("TEST 1: Truncate long conversation")
    print("=" * 80)

    # Create a long message history
    messages = []

    # Add system messages (should be kept)
    messages.append(SystemMessage(content="Previous conversation summary: ..."))
    messages.append(SystemMessage(content="Web search results: ..."))

    # Add 20 user-assistant exchanges
    for i in range(20):
        messages.append(HumanMessage(content=f"User question {i}"))
        messages.append(AIMessage(content=f"Assistant response {i}"))

    print(f"Original message count: {len(messages)}")
    print(f"  - System messages: {sum(1 for m in messages if isinstance(m, SystemMessage))}")
    print(f"  - Conversation messages: {sum(1 for m in messages if not isinstance(m, SystemMessage))}")

    # Truncate to keep only 10 most recent
    truncated = _truncate_messages(messages, max_recent=10)

    print(f"\nTruncated message count: {len(truncated)}")
    print(f"  - System messages: {sum(1 for m in truncated if isinstance(m, SystemMessage))}")
    print(f"  - Conversation messages: {sum(1 for m in truncated if not isinstance(m, SystemMessage))}")

    # Verify system messages are kept
    system_count = sum(1 for m in truncated if isinstance(m, SystemMessage))
    assert system_count == 2, f"Expected 2 system messages, got {system_count}"

    # Verify recent messages are kept
    conversation_count = sum(1 for m in truncated if not isinstance(m, SystemMessage))
    assert conversation_count == 10, f"Expected 10 conversation messages, got {conversation_count}"

    # Verify the most recent messages are kept
    last_human = [m for m in truncated if isinstance(m, HumanMessage)][-1]
    assert "19" in last_human.content, "Most recent message not preserved"

    print("\n✅ Test 1 PASSED: Truncation preserves system messages and recent conversation")

    print("\n" + "=" * 80)
    print("TEST 2: Short conversation (no truncation needed)")
    print("=" * 80)

    short_messages = [
        SystemMessage(content="System message"),
        HumanMessage(content="Question 1"),
        AIMessage(content="Answer 1"),
        HumanMessage(content="Question 2"),
        AIMessage(content="Answer 2"),
    ]

    truncated_short = _truncate_messages(short_messages, max_recent=10)

    print(f"Original: {len(short_messages)} messages")
    print(f"After truncation: {len(truncated_short)} messages")

    assert len(truncated_short) == len(short_messages), "Short conversation should not be truncated"

    print("\n✅ Test 2 PASSED: Short conversations are not modified")

    print("\n" + "=" * 80)
    print("TEST 3: Progressive truncation levels")
    print("=" * 80)

    # Test different truncation levels
    truncation_levels = [10, 6, 3]

    for level in truncation_levels:
        truncated = _truncate_messages(messages, max_recent=level)
        conversation_count = sum(1 for m in truncated if not isinstance(m, SystemMessage))
        print(f"Truncation level {level}: {conversation_count} conversation messages retained")
        assert conversation_count == level, f"Expected {level} messages, got {conversation_count}"

    print("\n✅ Test 3 PASSED: Progressive truncation works correctly")

    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED")
    print("=" * 80)


if __name__ == "__main__":
    test_truncate_messages()
