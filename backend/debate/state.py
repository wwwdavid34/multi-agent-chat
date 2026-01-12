"""Debate state models for AG2 backend.

Simplified state schema compared to LangGraph (9 fields vs 17).
AG2 handles message history internally, so we only store debate-specific state.
"""

from typing import TypedDict, Literal, Optional, Dict, List, Any

# Debate mode controls how the debate runs
# - autonomous: Runs until consensus or max_rounds (no pauses)
# - supervised: Pauses each round for user to review/vote (no input)
# - participatory: Pauses each round for user input and interaction
DebateMode = Literal["autonomous", "supervised", "participatory"]


class StanceData(TypedDict, total=False):
    """Structured stance information extracted from panelist response."""
    panelist_name: str
    stance: str  # 'FOR', 'AGAINST', 'CONDITIONAL', 'NEUTRAL'
    core_claim: str
    confidence: float  # 0.0-1.0
    changed_from_previous: bool
    change_explanation: Optional[str]


class ArgumentUnit(TypedDict, total=False):
    """Single argument unit (claim, evidence, challenge, concession)."""
    id: int
    panelist_name: str
    unit_type: str  # 'claim', 'evidence', 'challenge', 'concession'
    content: str
    target_claim_id: Optional[int]  # For challenges/concessions
    confidence: Optional[float]


class QualityMetrics(TypedDict, total=False):
    """Quality metrics for a debate round."""
    responsiveness_scores: Dict[str, float]  # panelist_name -> score
    claims_addressed: Dict[str, int]  # panelist_name -> count
    claims_missed: Dict[str, int]  # panelist_name -> count
    tags_used: Dict[str, int]  # panelist_name -> count
    concessions_detected: List[int]  # argument unit IDs
    evidence_strength: Dict[str, float]  # panelist_name -> score


class ScoreEventData(TypedDict, total=False):
    """A single scoring event (reward or penalty)."""
    category: str  # e.g., "responsiveness", "evidence", "user_approval"
    points: int  # Positive for rewards, negative for penalties
    reason: str  # Human-readable explanation


class RoundScoreData(TypedDict, total=False):
    """Score breakdown for a panelist in one round."""
    panelist_name: str
    round_number: int
    events: List[ScoreEventData]
    round_total: int
    cumulative_total: int


class DebateRound(TypedDict, total=False):
    """Single debate round result.

    Extended with structured quality data while maintaining API compatibility.
    New fields are optional (total=False) so old consumers still work.
    """
    round_number: int
    panel_responses: Dict[str, str]  # panelist_name -> response_text
    consensus_reached: bool
    user_message: Optional[str]

    # Quality tracking fields (new)
    stances: Optional[Dict[str, StanceData]]  # panelist_name -> stance
    argument_graph: Optional[List[ArgumentUnit]]  # All argument units this round
    quality_metrics: Optional[QualityMetrics]  # Responsiveness, engagement metrics

    # Scoring fields (Phase 3: Human-in-the-loop)
    scores: Optional[Dict[str, RoundScoreData]]  # panelist_name -> round score


class AssignedRole(TypedDict, total=False):
    """Explicit role assignment for a panelist in adversarial debates."""
    panelist_name: str
    role: Literal["PRO", "CON", "DEVIL_ADVOCATE", "NEUTRAL"]
    position_statement: str  # What they must argue for
    constraints: List[str]  # What they must/must not do


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

    # Debate mode configuration (simplified from separate flags)
    # - autonomous: runs without pauses
    # - supervised: pauses for review/voting
    # - participatory: pauses for user input
    debate_mode: DebateMode
    tagged_panelists: List[str]  # List of @mentioned panelist names

    # Results (populated during moderation phase)
    summary: Optional[str]  # Final moderated summary
    panel_responses: Dict[str, str]  # Latest panel responses
    debate_history: List[DebateRound]  # All debate rounds

    # Question being discussed (transient, not persisted)
    question: Optional[str]

    # Panelist configuration
    panelists: Optional[List[Dict[str, Any]]]  # PanelistConfig list
    provider_keys: Optional[Dict[str, str]]  # API keys for each provider

    # User message injection (for participatory mode)
    user_message: Optional[str]  # User's message to inject into next round

    # Adversarial role assignment (Phase 2)
    assigned_roles: Optional[Dict[str, AssignedRole]]  # panelist_name -> role
    stance_mode: Optional[Literal["free", "adversarial", "assigned"]]  # Stance assignment mode


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
