"""Usage tracking for debate sessions.

Accumulates token usage across all agents and debate rounds.
Returns API-compatible usage format.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def track_usage(agent_name: str, response: str) -> Dict[str, int]:
    """Extract token usage from AG2 agent response.

    AG2 agents return string responses; usage is available from the agent's
    last message metadata if available.

    Args:
        agent_name: Name of the agent
        response: Response string from AG2 agent

    Returns:
        Dict with input_tokens, output_tokens, total_tokens
    """
    # AG2 responses are strings; detailed token counts would come from
    # the underlying LLM client's response metadata.
    # For now, return a placeholder structure that can be enhanced later.
    return {
        "agent": agent_name,
        "input_tokens": 0,
        "output_tokens": 0,
        "total_tokens": 0,
    }


class UsageAccumulator:
    """Accumulates token usage across a debate session.

    Tracks calls from each agent and provides API-compatible summary.
    """

    def __init__(self):
        """Initialize empty usage tracker."""
        self.calls: List[Dict[str, Any]] = []

    def add(self, agent_name: str, response: str) -> None:
        """Add usage from an agent response.

        Args:
            agent_name: Name of agent that generated response
            response: Response string from agent
        """
        usage = track_usage(agent_name, response)
        self.calls.append(usage)
        logger.debug(f"Added usage for {agent_name}: {usage}")

    def summarize(self) -> Dict[str, int]:
        """Return API-compatible usage summary.

        Format matches frontend AskResponse.usage:
        {
            "total_input_tokens": int,
            "total_output_tokens": int,
            "total_tokens": int,
            "call_count": int,
        }

        Returns:
            Usage summary dict
        """
        total_input = sum(call.get("input_tokens", 0) for call in self.calls)
        total_output = sum(call.get("output_tokens", 0) for call in self.calls)

        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "total_tokens": total_input + total_output,
            "call_count": len(self.calls),
        }

    def reset(self) -> None:
        """Clear accumulated usage (for testing)."""
        self.calls = []
