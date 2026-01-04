"""Usage tracking for debate sessions.

Accumulates token usage across all agents and debate rounds.
Returns API-compatible usage format.
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def track_usage(agent_name: str, response: Dict[str, Any]) -> Dict[str, int]:
    """Extract token usage from AG2 agent response.

    AG2 responses include usage metadata from the LLM.

    Args:
        agent_name: Name of the agent
        response: Response dict from AG2 agent

    Returns:
        Dict with input_tokens, output_tokens, total_tokens
    """
    # Will be implemented in Phase 3
    raise NotImplementedError("Implement in Phase 3")


class UsageAccumulator:
    """Accumulates token usage across a debate session.

    Tracks calls from each agent and provides API-compatible summary.
    """

    def __init__(self):
        """Initialize empty usage tracker."""
        self.calls: List[Dict[str, Any]] = []

    def add(self, agent_name: str, response: Dict[str, Any]) -> None:
        """Add usage from an agent response.

        Args:
            agent_name: Name of agent that generated response
            response: Response dict from agent
        """
        raise NotImplementedError("Implement in Phase 3")

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
        raise NotImplementedError("Implement in Phase 3")

    def reset(self) -> None:
        """Clear accumulated usage (for testing)."""
        self.calls = []
