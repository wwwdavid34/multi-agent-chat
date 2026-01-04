"""AG2 agent factory functions for debate participants.

Creates and configures agents for panelists, moderator, and user participation.
"""

from typing import Dict, Any, Optional, Callable
import logging

logger = logging.getLogger(__name__)


# Placeholder - will be implemented in Phase 2
def create_panelist_agent(config: Dict[str, Any], api_key: str) -> Any:
    """Create AG2 agent for a panelist.

    Args:
        config: PanelistConfig dict with id, name, provider, model
        api_key: API key for the provider

    Returns:
        AG2 AssistantAgent configured for the panelist
    """
    raise NotImplementedError("Implement in Phase 2")


def create_moderator_agent(api_key: str) -> Any:
    """Create AG2 moderator agent (GPT-4o).

    Returns:
        AG2 AssistantAgent configured as moderator
    """
    raise NotImplementedError("Implement in Phase 2")


def create_user_proxy() -> Any:
    """Create user proxy agent for user-debate mode.

    Returns:
        AG2 UserProxyAgent configured for programmatic user input
    """
    raise NotImplementedError("Implement in Phase 2")


def create_search_tool() -> Callable[[str], str]:
    """Create Tavily search tool for AG2.

    Returns:
        Async function that takes a query and returns search results
    """
    raise NotImplementedError("Implement in Phase 2")
