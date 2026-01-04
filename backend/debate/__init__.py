"""AG2-based debate orchestration module.

This module provides an alternative backend implementation to LangGraph,
using AG2 (AutoGen) for debate management while maintaining 100% API compatibility.
"""

from .service import AG2DebateService, DebateService
from .state import DebateState, DebateRound, DebateResult
from .orchestrator import DebateOrchestrator
from .agents import create_panelist_agent, create_moderator_agent, create_user_proxy, create_search_tool
from .persistence import DebateStorage, PostgresDebateStorage
from .usage import UsageAccumulator

__all__ = [
    "AG2DebateService",
    "DebateService",
    "DebateState",
    "DebateRound",
    "DebateResult",
    "DebateOrchestrator",
    "create_panelist_agent",
    "create_moderator_agent",
    "create_user_proxy",
    "create_search_tool",
    "DebateStorage",
    "PostgresDebateStorage",
    "UsageAccumulator",
]
