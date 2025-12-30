#!/usr/bin/env python3
"""
Test script for the streaming endpoint.
"""

import asyncio
import httpx


async def test_streaming():
    """Test the /ask-stream endpoint."""

    url = "http://localhost:8000/ask-stream"
    payload = {
        "thread_id": "test-stream",
        "question": "What is 2+2?",
        "attachments": [],
        "panelists": [
            {"id": "p1", "name": "Math Expert", "provider": "openai", "model": "gpt-4o-mini"}
        ],
        "provider_keys": {},
    }

    print("Testing streaming endpoint...")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream("POST", url, json=payload) as response:
            print(f"Status: {response.status_code}")
            print("Streaming events:")
            print("-" * 80)

            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = line[6:]  # Remove "data: " prefix
                    print(f"Event: {data}")

    print("-" * 80)
    print("Stream complete!")


if __name__ == "__main__":
    asyncio.run(test_streaming())
