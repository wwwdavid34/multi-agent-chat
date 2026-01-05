"""Debate state models for AG2 backend.

Simplified state schema compared to LangGraph (9 fields vs 17).
AG2 handles message history internally, so we only store debate-specific state.
"""

from typing import TypedDict, Literal, Optional, Dict, List, Any


class DebateRound(TypedDict):
    """Single debate round result - FROZEN structure for API compatibility.

    This structure is emitted in 'debate_round' SSE events and included in
    final results. Field names and types must never change.
    """
    round_number: int
    panel_responses: Dict[str, str]  # panelist_name -> response_text
    consensus_reached: bool
    user_message: Optional[str]


class DebateState(TypedDict, total=False):
    """Simplified debate state for AG2 implementation.

    Compared to old LangGraph PanelState (17 fields), this has only 9 fields:
    - Removed: messages, conversation_summary, search_results, search_sources,
               needs_search, debate_paused, usage_accumulator
    - Reason: AG2 handles these internally or we track separately

    total=False allows optional fields to be omitted.
    """
    # Core identifiers
    thread_id: str

    # Phase control (deterministic state machine)
    phase: Literal["init", "debate", "paused", "moderation", "finished"]

    # Debate tracking
    debate_round: int  # Current round number (0-indexed)
    max_rounds: int  # Maximum debate rounds
    consensus_reached: bool  # Whether consensus was reached

    # Debate configuration
    debate_mode: bool  # Enable/disable debate feature
    user_as_participant: bool  # User is participant in debate
    tagged_panelists: List[str]  # List of tagged panelist names

    # Results (populated during moderation phase)
    summary: Optional[str]  # Final moderated summary
    panel_responses: Dict[str, str]  # Latest panel responses
    debate_history: List[DebateRound]  # All debate rounds

    # Question being discussed (transient, not persisted)
    question: Optional[str]

    # Configuration flags
    step_review: Optional[bool]  # Pause after each debate round
    continue_debate: Optional[bool]  # Resume from pause

    # Panelist configuration
    panelists: Optional[List[Dict[str, Any]]]  # PanelistConfig list
    provider_keys: Optional[Dict[str, str]]  # API keys for each provider


class DebateResult(TypedDict, total=False):
    """Final result structure matching API response format.

    This is what gets emitted in 'result' SSE event and returned from endpoints.
    Must match AskResponse schema for frontend compatibility.
    """
    thread_id: str
    summary: str
    panel_responses: Dict[str, str]
    debate_history: List[DebateRound]
    usage: Optional[Dict[str, int]]
    debate_paused: bool
