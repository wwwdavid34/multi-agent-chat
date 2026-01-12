"""Debate scoring system.

Tracks and calculates points for panelist behaviors during debates.
Scoring is used to:
1. Display real-time scores to users
2. Provide feedback to agents to improve debate quality
3. Trigger forced concessions when one panelist falls too far behind
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


@dataclass
class ScoreEvent:
    """A single scoring event (reward or penalty)."""
    category: str
    points: int
    reason: str


@dataclass
class RoundScore:
    """Score breakdown for a panelist in one round."""
    panelist_name: str
    round_number: int
    events: List[ScoreEvent] = field(default_factory=list)
    round_total: int = 0
    cumulative_total: int = 0


@dataclass
class PanelistScoreState:
    """Running score state for a panelist across rounds."""
    cumulative: int = 0
    events_history: List[ScoreEvent] = field(default_factory=list)
    ignored_claims: List[str] = field(default_factory=list)


class DebateScorer:
    """Calculate and track debate scores.

    Scoring incentivizes:
    - Responsiveness (addressing opponent claims)
    - Evidence-based arguments
    - Novel perspectives
    - Acknowledgment of valid points (concessions)
    - Consistent stance
    - User approval

    Scoring penalizes:
    - Ignoring opponent arguments
    - Drifting from declared stance
    - Excessive hedging
    - Logical fallacies
    - User disapproval
    """

    # Scoring rules with point values
    SCORING_RULES = {
        # Rewards
        "addressed_claim": 10,      # Responded to opponent's claim
        "provided_evidence": 8,     # Gave concrete evidence/examples
        "novel_perspective": 8,     # Introduced new angle
        "won_concession": 15,       # Got opponent to concede a point
        "stance_consistent": 5,     # Maintained declared position
        "user_compelling": 24,      # User upvoted (2x weight)

        # Penalties
        "ignored_claim": -10,       # Failed to address opponent's claim
        "stance_drift": -15,        # Changed position without justification
        "excessive_hedging": -5,    # Too many qualifiers/equivocations
        "logical_fallacy": -10,     # Used fallacious reasoning
        "user_weak": -16,           # User downvoted (2x weight)
    }

    # Points behind leader to trigger forced concession
    FORCED_CONCESSION_GAP = 30

    def __init__(self):
        """Initialize scorer with empty state."""
        self.scores: Dict[str, PanelistScoreState] = {}
        self.current_round: int = 0

    def reset(self) -> None:
        """Reset all scores for a new debate."""
        self.scores = {}
        self.current_round = 0

    def _get_or_create_score_state(self, panelist_name: str) -> PanelistScoreState:
        """Get or create score state for a panelist."""
        if panelist_name not in self.scores:
            self.scores[panelist_name] = PanelistScoreState()
        return self.scores[panelist_name]

    async def score_round(
        self,
        panelist_name: str,
        response: str,
        opponent_claims: List[str],
        declared_stance: Optional[str] = None,
        previous_arguments: Optional[List[str]] = None,
        current_stance: Optional[str] = None,
        evidence_count: int = 0,
        novel_arguments: int = 0,
        user_votes: Optional[Dict[str, int]] = None,
    ) -> RoundScore:
        """Score a panelist's response for one round.

        Args:
            panelist_name: Name of the panelist
            response: The panelist's response text
            opponent_claims: List of claims from opponents to address
            declared_stance: Panelist's declared position
            previous_arguments: Panelist's previous arguments
            current_stance: Extracted stance from current response
            evidence_count: Number of evidence units found
            novel_arguments: Number of new arguments introduced
            user_votes: Dict with 'compelling' and 'weak' counts

        Returns:
            RoundScore with events and totals
        """
        events: List[ScoreEvent] = []
        state = self._get_or_create_score_state(panelist_name)

        # 1. Responsiveness - addressed opponent claims
        addressed_count = await self._count_addressed_claims(response, opponent_claims)
        if addressed_count > 0:
            points = addressed_count * self.SCORING_RULES["addressed_claim"]
            events.append(ScoreEvent(
                category="responsiveness",
                points=points,
                reason=f"Addressed {addressed_count} opponent claim(s)"
            ))

        # 2. Penalties for ignored claims
        ignored_count = len(opponent_claims) - addressed_count
        if ignored_count > 0 and opponent_claims:
            points = ignored_count * self.SCORING_RULES["ignored_claim"]
            events.append(ScoreEvent(
                category="ignored_claim",
                points=points,
                reason=f"Ignored {ignored_count} opponent claim(s)"
            ))
            # Track ignored claims for feedback
            state.ignored_claims = opponent_claims[addressed_count:]

        # 3. Evidence points (capped at 3 evidence units per round)
        if evidence_count > 0:
            capped_evidence = min(evidence_count, 3)
            points = capped_evidence * self.SCORING_RULES["provided_evidence"]
            events.append(ScoreEvent(
                category="evidence",
                points=points,
                reason=f"Provided {evidence_count} piece(s) of evidence"
            ))

        # 4. Novel perspective points
        if novel_arguments > 0:
            points = min(novel_arguments, 2) * self.SCORING_RULES["novel_perspective"]
            events.append(ScoreEvent(
                category="novelty",
                points=points,
                reason=f"Introduced {novel_arguments} new perspective(s)"
            ))

        # 5. Stance consistency
        if declared_stance and current_stance:
            if self._stances_match(declared_stance, current_stance):
                events.append(ScoreEvent(
                    category="stance_consistency",
                    points=self.SCORING_RULES["stance_consistent"],
                    reason="Maintained consistent stance"
                ))
            else:
                # Check if there was justification for change
                has_justification = await self._has_stance_change_justification(response)
                if not has_justification:
                    events.append(ScoreEvent(
                        category="stance_drift",
                        points=self.SCORING_RULES["stance_drift"],
                        reason="Changed stance without justification"
                    ))

        # 6. User votes (2x weight)
        if user_votes:
            if user_votes.get("compelling", 0) > 0:
                events.append(ScoreEvent(
                    category="user_approval",
                    points=self.SCORING_RULES["user_compelling"],
                    reason="User marked as compelling"
                ))
            if user_votes.get("weak", 0) > 0:
                events.append(ScoreEvent(
                    category="user_disapproval",
                    points=self.SCORING_RULES["user_weak"],
                    reason="User marked as weak"
                ))

        # 7. Check for hedging
        hedge_count = self._count_hedging(response)
        if hedge_count >= 5:  # Excessive hedging threshold
            events.append(ScoreEvent(
                category="hedging",
                points=self.SCORING_RULES["excessive_hedging"],
                reason=f"Excessive hedging ({hedge_count} qualifiers)"
            ))

        # Calculate totals
        round_total = sum(e.points for e in events)
        state.cumulative += round_total
        state.events_history.extend(events)

        return RoundScore(
            panelist_name=panelist_name,
            round_number=self.current_round,
            events=events,
            round_total=round_total,
            cumulative_total=state.cumulative
        )

    async def _count_addressed_claims(self, response: str, claims: List[str]) -> int:
        """Count how many opponent claims were addressed in response.

        Uses simple keyword matching. Could be enhanced with semantic similarity.
        """
        if not claims:
            return 0

        response_lower = response.lower()
        addressed = 0

        for claim in claims:
            # Extract key phrases from claim
            claim_words = set(claim.lower().split())
            # Remove common words
            claim_words -= {"the", "a", "an", "is", "are", "was", "were", "that", "this", "it"}

            # Check if enough key words appear in response
            matching_words = sum(1 for word in claim_words if word in response_lower)
            if matching_words >= min(3, len(claim_words) * 0.5):
                addressed += 1

        return addressed

    def _stances_match(self, stance1: str, stance2: str) -> bool:
        """Check if two stances are the same position."""
        s1 = stance1.upper().strip()
        s2 = stance2.upper().strip()
        return s1 == s2

    async def _has_stance_change_justification(self, response: str) -> bool:
        """Check if response contains justification for stance change.

        Looks for phrases indicating reasoned change of position.
        """
        justification_phrases = [
            "i've reconsidered",
            "you raise a good point",
            "you're right about",
            "i concede",
            "upon reflection",
            "i now agree",
            "you've convinced me",
            "i was wrong about",
            "given this evidence",
            "the evidence suggests",
        ]

        response_lower = response.lower()
        return any(phrase in response_lower for phrase in justification_phrases)

    def _count_hedging(self, response: str) -> int:
        """Count hedging language in response."""
        hedging_words = [
            "maybe", "perhaps", "possibly", "might", "could be",
            "it seems", "i think", "arguably", "some would say",
            "in a way", "sort of", "kind of", "to some extent",
        ]

        response_lower = response.lower()
        count = sum(response_lower.count(word) for word in hedging_words)
        return count

    def get_scores(self, panelist_name: str) -> Optional[PanelistScoreState]:
        """Get current score state for a panelist."""
        return self.scores.get(panelist_name)

    def get_all_scores(self) -> Dict[str, int]:
        """Get cumulative scores for all panelists."""
        return {
            name: state.cumulative
            for name, state in self.scores.items()
        }

    def get_leader(self) -> Optional[tuple[str, int]]:
        """Get the panelist with the highest score."""
        if not self.scores:
            return None

        leader = max(self.scores.items(), key=lambda x: x[1].cumulative)
        return (leader[0], leader[1].cumulative)

    def get_score_gap(self, panelist_name: str) -> int:
        """Get points behind the leader for a panelist."""
        leader = self.get_leader()
        if not leader:
            return 0

        state = self.scores.get(panelist_name)
        if not state:
            return leader[1]

        return leader[1] - state.cumulative

    def should_force_concession(self, panelist_name: str) -> bool:
        """Check if panelist is far enough behind to force a concession."""
        gap = self.get_score_gap(panelist_name)
        return gap >= self.FORCED_CONCESSION_GAP

    def get_forced_concession_prompt(self, panelist_name: str) -> Optional[str]:
        """Generate prompt for forced concession if needed.

        Returns prompt text if panelist should make a concession, None otherwise.
        """
        if not self.should_force_concession(panelist_name):
            return None

        leader = self.get_leader()
        if not leader:
            return None

        leader_name, leader_score = leader
        gap = self.get_score_gap(panelist_name)

        return f"""
IMPORTANT: You are currently {gap} points behind {leader_name} in this debate.
To demonstrate intellectual honesty and potentially recover points:
- Acknowledge at least ONE strong point from {leader_name}'s argument
- Explain what specifically made that point compelling
- Then continue to make your own arguments

This concession requirement is triggered when a panelist falls {self.FORCED_CONCESSION_GAP}+ points behind.
"""

    def record_user_vote(
        self,
        panelist_name: str,
        round_number: int,
        vote_type: str  # "compelling" or "weak"
    ) -> ScoreEvent:
        """Record a user vote and return the resulting score event.

        Args:
            panelist_name: Name of the panelist being voted on
            round_number: Round the vote applies to
            vote_type: Either "compelling" or "weak"

        Returns:
            ScoreEvent with the vote result
        """
        state = self._get_or_create_score_state(panelist_name)

        if vote_type == "compelling":
            event = ScoreEvent(
                category="user_approval",
                points=self.SCORING_RULES["user_compelling"],
                reason="User marked as compelling"
            )
        else:
            event = ScoreEvent(
                category="user_disapproval",
                points=self.SCORING_RULES["user_weak"],
                reason="User marked as weak"
            )

        state.cumulative += event.points
        state.events_history.append(event)

        logger.info(f"User vote recorded: {panelist_name} got {event.points} points ({vote_type})")

        return event

    def get_score_summary(self) -> Dict[str, Any]:
        """Get a summary of all scores for display.

        Returns:
            Dict with score data for each panelist, sorted by cumulative score
        """
        summary = {}

        for name, state in self.scores.items():
            # Get recent events (last 5)
            recent_events = state.events_history[-5:] if state.events_history else []

            summary[name] = {
                "cumulative": state.cumulative,
                "recent_events": [
                    {"category": e.category, "points": e.points, "reason": e.reason}
                    for e in recent_events
                ],
                "ignored_claims": state.ignored_claims,
            }

        # Sort by cumulative score descending
        sorted_summary = dict(
            sorted(summary.items(), key=lambda x: x[1]["cumulative"], reverse=True)
        )

        return sorted_summary

    def advance_round(self) -> None:
        """Advance to the next round."""
        self.current_round += 1
        # Clear ignored claims for new round
        for state in self.scores.values():
            state.ignored_claims = []
