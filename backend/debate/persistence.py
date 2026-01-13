"""Persistence layer for debate state.

Simple JSON-based storage in PostgreSQL.
No LangGraph checkpointer complexity - just save/load state as JSON.
"""

import json
import logging
from typing import Protocol, Dict, Any, Optional, List

from .state import DebateState

logger = logging.getLogger(__name__)

try:
    import asyncpg
except ImportError:
    asyncpg = None


class DebateStorage(Protocol):
    """Storage interface for debate state.

    Allows different implementations (PostgreSQL, Redis, etc.)
    without tightly coupling the orchestrator.
    """

    async def load(self, thread_id: str) -> DebateState:
        """Load debate state for a thread.

        Args:
            thread_id: Unique thread identifier

        Returns:
            DebateState dict

        Raises:
            ValueError: If state not found
        """
        ...

    async def save(self, thread_id: str, state: DebateState) -> None:
        """Save debate state for a thread.

        Args:
            thread_id: Unique thread identifier
            state: DebateState to persist
        """
        ...


class PostgresDebateStorage:
    """PostgreSQL implementation of DebateStorage.

    Stores state as JSON in a simple debate_state table.
    Simpler than LangGraph checkpointing - no threading hacks.

    Expected table schema:
    CREATE TABLE debate_state (
        thread_id TEXT PRIMARY KEY,
        state JSONB NOT NULL,
        updated_at TIMESTAMP DEFAULT NOW()
    );
    """

    def __init__(self, conn_string: str):
        """Initialize with PostgreSQL connection string.

        Args:
            conn_string: asyncpg connection string
        """
        if asyncpg is None:
            raise RuntimeError("asyncpg not installed. Install with: pip install asyncpg")

        self.conn_string = conn_string
        self._pool: Optional[Any] = None

    async def _get_pool(self):
        """Get or create database connection pool."""
        if self._pool is None:
            self._pool = await asyncpg.create_pool(self.conn_string, min_size=1, max_size=5)
            await self._ensure_table()
        return self._pool

    async def _ensure_table(self) -> None:
        """Create debate_state table and quality tracking tables if they don't exist."""
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            # Main debate state table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS debate_state (
                    thread_id TEXT PRIMARY KEY,
                    state JSONB NOT NULL,
                    updated_at TIMESTAMP DEFAULT NOW()
                );
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_debate_state_updated ON debate_state(updated_at);
            """)
            
            # Argument units table (claims, evidence, challenges, concessions)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS argument_units (
                    id SERIAL PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    round_number INT NOT NULL,
                    panelist_name TEXT NOT NULL,
                    unit_type TEXT NOT NULL,  -- 'claim', 'evidence', 'challenge', 'concession'
                    content TEXT NOT NULL,
                    target_claim_id INT,  -- For challenges/concessions
                    confidence FLOAT,  -- 0.0-1.0
                    metadata JSONB,  -- Additional context
                    created_at TIMESTAMP DEFAULT NOW(),
                    FOREIGN KEY (target_claim_id) REFERENCES argument_units(id) ON DELETE SET NULL
                );
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_argument_units_thread ON argument_units(thread_id);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_argument_units_round ON argument_units(thread_id, round_number);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_argument_units_type ON argument_units(unit_type);
            """)
            
            # Stance history table (positions per round)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS stance_history (
                    id SERIAL PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    round_number INT NOT NULL,
                    panelist_name TEXT NOT NULL,
                    stance TEXT NOT NULL,  -- 'FOR', 'AGAINST', 'NEUTRAL'
                    core_claim TEXT NOT NULL,
                    confidence FLOAT NOT NULL,  -- 0.0-1.0
                    changed_from_previous BOOLEAN DEFAULT FALSE,
                    change_explanation TEXT,  -- Required if changed
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(thread_id, round_number, panelist_name)
                );
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stance_history_thread ON stance_history(thread_id);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stance_history_panelist ON stance_history(thread_id, panelist_name);
            """)
            
            # Responsiveness scores table (engagement metrics)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS responsiveness_scores (
                    id SERIAL PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    round_number INT NOT NULL,
                    panelist_name TEXT NOT NULL,
                    score FLOAT NOT NULL,  -- 0.0-1.0
                    claims_addressed INT NOT NULL,
                    claims_missed INT NOT NULL,
                    tags_used INT NOT NULL,
                    missed_arguments JSONB,  -- List of argument IDs not addressed
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(thread_id, round_number, panelist_name)
                );
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_responsiveness_thread ON responsiveness_scores(thread_id);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_responsiveness_panelist ON responsiveness_scores(thread_id, panelist_name);
            """)

            # Debate scores table (Phase 3: Human-in-the-loop scoring)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS debate_scores (
                    id SERIAL PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    round_number INT NOT NULL,
                    panelist_name TEXT NOT NULL,

                    -- Point breakdown
                    responsiveness_points INT DEFAULT 0,
                    evidence_points INT DEFAULT 0,
                    novelty_points INT DEFAULT 0,
                    concession_won_points INT DEFAULT 0,
                    stance_consistency_points INT DEFAULT 0,
                    user_compelling_points INT DEFAULT 0,

                    -- Penalties
                    ignored_claim_penalty INT DEFAULT 0,
                    stance_drift_penalty INT DEFAULT 0,
                    hedging_penalty INT DEFAULT 0,
                    fallacy_penalty INT DEFAULT 0,
                    user_weak_penalty INT DEFAULT 0,

                    -- Totals
                    round_total INT DEFAULT 0,
                    cumulative_total INT DEFAULT 0,

                    -- Score events as JSON
                    events JSONB,

                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(thread_id, round_number, panelist_name)
                );
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_debate_scores_thread ON debate_scores(thread_id);
            """)
            await conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_debate_scores_panelist ON debate_scores(thread_id, panelist_name);
            """)

            logger.debug("Ensured debate_state and quality tracking tables exist")

    async def save(self, thread_id: str, state: DebateState) -> None:
        """Save state as JSON to PostgreSQL.

        Args:
            thread_id: Thread identifier
            state: State to save
        """
        try:
            pool = await self._get_pool()
            state_json = json.dumps(state)

            async with pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO debate_state (thread_id, state, updated_at)
                    VALUES ($1, $2, NOW())
                    ON CONFLICT (thread_id) DO UPDATE
                    SET state = $2, updated_at = NOW()
                """, thread_id, state_json)

            logger.debug(f"Saved debate state for thread {thread_id}")
        except Exception as e:
            logger.error(f"Error saving debate state for {thread_id}: {e}")
            raise

    async def load(self, thread_id: str) -> DebateState:
        """Load state from PostgreSQL JSON.

        Args:
            thread_id: Thread identifier

        Returns:
            DebateState

        Raises:
            ValueError: If state not found
        """
        try:
            pool = await self._get_pool()

            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT state FROM debate_state WHERE thread_id = $1",
                    thread_id
                )

            if not row:
                raise ValueError(f"No debate state found for thread {thread_id}")

            state_data = row["state"]
            # Handle both string and dict (asyncpg may return dict for JSONB)
            if isinstance(state_data, str):
                state = json.loads(state_data)
            else:
                state = state_data

            logger.debug(f"Loaded debate state for thread {thread_id}")
            return state
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error loading debate state for {thread_id}: {e}")
            raise


    async def save_argument_unit(self, thread_id: str, round_number: int, 
                                 panelist_name: str, unit_type: str, 
                                 content: str, target_claim_id: Optional[int] = None,
                                 confidence: Optional[float] = None,
                                 metadata: Optional[Dict[str, Any]] = None) -> int:
        """Save an argument unit and return its ID.
        
        Args:
            thread_id: Thread identifier
            round_number: Debate round number
            panelist_name: Name of panelist who made the argument
            unit_type: Type of argument unit ('claim', 'evidence', 'challenge', 'concession')
            content: Text content of the argument
            target_claim_id: ID of claim this unit refers to (for challenges/concessions)
            confidence: Confidence score 0.0-1.0
            metadata: Additional context as JSON
            
        Returns:
            ID of the created argument unit
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO argument_units 
                (thread_id, round_number, panelist_name, unit_type, content, 
                 target_claim_id, confidence, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id
            """, thread_id, round_number, panelist_name, unit_type, content,
                target_claim_id, confidence, json.dumps(metadata) if metadata else None)
            return row['id']
    
    async def save_stance(self, thread_id: str, round_number: int,
                         panelist_name: str, stance: str, core_claim: str,
                         confidence: float, changed_from_previous: bool = False,
                         change_explanation: Optional[str] = None) -> None:
        """Save a panelist's stance for a round.
        
        Args:
            thread_id: Thread identifier
            round_number: Debate round number
            panelist_name: Name of panelist
            stance: Position ('FOR', 'AGAINST', 'NEUTRAL')
            core_claim: Main claim/position statement
            confidence: Confidence score 0.0-1.0
            changed_from_previous: Whether stance changed from previous round
            change_explanation: Explanation if stance changed
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO stance_history 
                (thread_id, round_number, panelist_name, stance, core_claim,
                 confidence, changed_from_previous, change_explanation)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (thread_id, round_number, panelist_name) DO UPDATE
                SET stance = $4, core_claim = $5, confidence = $6,
                    changed_from_previous = $7, change_explanation = $8
            """, thread_id, round_number, panelist_name, stance, core_claim,
                confidence, changed_from_previous, change_explanation)
    
    async def save_responsiveness_score(self, thread_id: str, round_number: int,
                                       panelist_name: str, score: float,
                                       claims_addressed: int, claims_missed: int,
                                       tags_used: int, missed_arguments: List[int]) -> None:
        """Save responsiveness score for a panelist in a round.
        
        Args:
            thread_id: Thread identifier
            round_number: Debate round number
            panelist_name: Name of panelist
            score: Responsiveness score 0.0-1.0
            claims_addressed: Number of opponent claims addressed
            claims_missed: Number of opponent claims ignored
            tags_used: Number of @Name tags used
            missed_arguments: List of argument unit IDs not addressed
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO responsiveness_scores
                (thread_id, round_number, panelist_name, score,
                 claims_addressed, claims_missed, tags_used, missed_arguments)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (thread_id, round_number, panelist_name) DO UPDATE
                SET score = $4, claims_addressed = $5, claims_missed = $6,
                    tags_used = $7, missed_arguments = $8
            """, thread_id, round_number, panelist_name, score,
                claims_addressed, claims_missed, tags_used, json.dumps(missed_arguments))
    
    async def get_previous_stance(self, thread_id: str, panelist_name: str,
                                 current_round: int) -> Optional[Dict[str, Any]]:
        """Get panelist's stance from previous round.
        
        Args:
            thread_id: Thread identifier
            panelist_name: Name of panelist
            current_round: Current round number
            
        Returns:
            Previous stance data or None if no previous stance
        """
        if current_round == 0:
            return None
            
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT stance, core_claim, confidence
                FROM stance_history
                WHERE thread_id = $1 AND panelist_name = $2 AND round_number = $3
            """, thread_id, panelist_name, current_round - 1)
            
            if row:
                return dict(row)
            return None
    
    async def get_round_arguments(self, thread_id: str, round_number: int) -> List[Dict[str, Any]]:
        """Get all argument units from a specific round.

        Args:
            thread_id: Thread identifier
            round_number: Round number

        Returns:
            List of argument unit dictionaries
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, panelist_name, unit_type, content, target_claim_id, confidence, metadata
                FROM argument_units
                WHERE thread_id = $1 AND round_number = $2
                ORDER BY id
            """, thread_id, round_number)

            return [dict(row) for row in rows]

    async def save_round_scores(self, thread_id: str, round_number: int,
                                scores: Dict[str, Any]) -> None:
        """Save debate scores for all panelists in a round.

        Args:
            thread_id: Thread identifier
            round_number: Debate round number
            scores: Dict mapping panelist_name to RoundScore data
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            for panelist_name, score_data in scores.items():
                # Extract point breakdowns from events
                points = {
                    'responsiveness': 0, 'evidence': 0, 'novelty': 0,
                    'stance_consistency': 0, 'user_approval': 0,
                    'ignored_claim': 0, 'stance_drift': 0, 'hedging': 0, 'user_disapproval': 0
                }

                events = score_data.get('events', [])
                for event in events:
                    category = event.get('category', '')
                    event_points = event.get('points', 0)
                    if category in points:
                        points[category] += event_points

                await conn.execute("""
                    INSERT INTO debate_scores
                    (thread_id, round_number, panelist_name,
                     responsiveness_points, evidence_points, novelty_points,
                     stance_consistency_points, user_compelling_points,
                     ignored_claim_penalty, stance_drift_penalty, hedging_penalty,
                     user_weak_penalty, round_total, cumulative_total, events)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                    ON CONFLICT (thread_id, round_number, panelist_name) DO UPDATE
                    SET responsiveness_points = $4, evidence_points = $5, novelty_points = $6,
                        stance_consistency_points = $7, user_compelling_points = $8,
                        ignored_claim_penalty = $9, stance_drift_penalty = $10, hedging_penalty = $11,
                        user_weak_penalty = $12, round_total = $13, cumulative_total = $14, events = $15
                """, thread_id, round_number, panelist_name,
                    points['responsiveness'], points['evidence'], points['novelty'],
                    points['stance_consistency'], points['user_approval'],
                    abs(points['ignored_claim']), abs(points['stance_drift']), abs(points['hedging']),
                    abs(points['user_disapproval']),
                    score_data.get('round_total', 0),
                    score_data.get('cumulative_total', 0),
                    json.dumps([{'category': e['category'], 'points': e['points'], 'reason': e['reason']}
                               for e in events]))

        logger.debug(f"Saved round {round_number} scores for {len(scores)} panelists")

    async def save_user_vote(self, thread_id: str, round_number: int,
                            panelist_name: str, vote_type: str,
                            points: int) -> None:
        """Record a user vote on a panelist's response.

        Args:
            thread_id: Thread identifier
            round_number: Debate round number
            panelist_name: Name of panelist being voted on
            vote_type: Either "compelling" or "weak"
            points: Points to add (positive for compelling, negative for weak)
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            if vote_type == "compelling":
                await conn.execute("""
                    UPDATE debate_scores
                    SET user_compelling_points = user_compelling_points + $4,
                        round_total = round_total + $4,
                        cumulative_total = cumulative_total + $4
                    WHERE thread_id = $1 AND round_number = $2 AND panelist_name = $3
                """, thread_id, round_number, panelist_name, points)
            else:
                await conn.execute("""
                    UPDATE debate_scores
                    SET user_weak_penalty = user_weak_penalty + $4,
                        round_total = round_total - $4,
                        cumulative_total = cumulative_total - $4
                    WHERE thread_id = $1 AND round_number = $2 AND panelist_name = $3
                """, thread_id, round_number, panelist_name, abs(points))

        logger.debug(f"Recorded user vote ({vote_type}) for {panelist_name} round {round_number}")

    async def get_cumulative_scores(self, thread_id: str) -> Dict[str, int]:
        """Get cumulative scores for all panelists in a debate.

        Args:
            thread_id: Thread identifier

        Returns:
            Dict mapping panelist_name to cumulative score
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT panelist_name, MAX(cumulative_total) as total
                FROM debate_scores
                WHERE thread_id = $1
                GROUP BY panelist_name
                ORDER BY total DESC
            """, thread_id)

            return {row['panelist_name']: row['total'] for row in rows}

    async def get_round_scores(self, thread_id: str, round_number: int) -> Dict[str, Any]:
        """Get scores for a specific round.

        Args:
            thread_id: Thread identifier
            round_number: Round number

        Returns:
            Dict mapping panelist_name to score data
        """
        pool = await self._get_pool()
        async with pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT panelist_name, round_total, cumulative_total, events
                FROM debate_scores
                WHERE thread_id = $1 AND round_number = $2
            """, thread_id, round_number)

            result = {}
            for row in rows:
                events = row['events']
                if isinstance(events, str):
                    events = json.loads(events)
                result[row['panelist_name']] = {
                    'round_total': row['round_total'],
                    'cumulative_total': row['cumulative_total'],
                    'events': events or []
                }
            return result


class InMemoryDebateStorage:
    """In-memory implementation for testing.

    Simple dict-based storage - not for production.
    """

    def __init__(self):
        """Initialize empty storage."""
        self.states: Dict[str, DebateState] = {}
        self.argument_units: List[Dict[str, Any]] = []
        self.stances: List[Dict[str, Any]] = []
        self.responsiveness: List[Dict[str, Any]] = []
        self._next_id = 1

    async def save(self, thread_id: str, state: DebateState) -> None:
        """Save state to memory."""
        self.states[thread_id] = state

    async def load(self, thread_id: str) -> DebateState:
        """Load state from memory."""
        if thread_id not in self.states:
            raise ValueError(f"No state found for thread {thread_id}")
        return self.states[thread_id]
    
    async def save_argument_unit(self, thread_id: str, round_number: int,
                                 panelist_name: str, unit_type: str,
                                 content: str, target_claim_id: Optional[int] = None,
                                 confidence: Optional[float] = None,
                                 metadata: Optional[Dict[str, Any]] = None) -> int:
        """Save argument unit in memory."""
        unit_id = self._next_id
        self._next_id += 1
        self.argument_units.append({
            'id': unit_id,
            'thread_id': thread_id,
            'round_number': round_number,
            'panelist_name': panelist_name,
            'unit_type': unit_type,
            'content': content,
            'target_claim_id': target_claim_id,
            'confidence': confidence,
            'metadata': metadata
        })
        return unit_id
    
    async def save_stance(self, thread_id: str, round_number: int,
                         panelist_name: str, stance: str, core_claim: str,
                         confidence: float, changed_from_previous: bool = False,
                         change_explanation: Optional[str] = None) -> None:
        """Save stance in memory."""
        self.stances = [s for s in self.stances 
                       if not (s['thread_id'] == thread_id and 
                              s['round_number'] == round_number and 
                              s['panelist_name'] == panelist_name)]
        self.stances.append({
            'thread_id': thread_id,
            'round_number': round_number,
            'panelist_name': panelist_name,
            'stance': stance,
            'core_claim': core_claim,
            'confidence': confidence,
            'changed_from_previous': changed_from_previous,
            'change_explanation': change_explanation
        })
    
    async def save_responsiveness_score(self, thread_id: str, round_number: int,
                                       panelist_name: str, score: float,
                                       claims_addressed: int, claims_missed: int,
                                       tags_used: int, missed_arguments: List[int]) -> None:
        """Save responsiveness score in memory."""
        self.responsiveness = [r for r in self.responsiveness
                              if not (r['thread_id'] == thread_id and
                                     r['round_number'] == round_number and
                                     r['panelist_name'] == panelist_name)]
        self.responsiveness.append({
            'thread_id': thread_id,
            'round_number': round_number,
            'panelist_name': panelist_name,
            'score': score,
            'claims_addressed': claims_addressed,
            'claims_missed': claims_missed,
            'tags_used': tags_used,
            'missed_arguments': missed_arguments
        })
    
    async def get_previous_stance(self, thread_id: str, panelist_name: str,
                                 current_round: int) -> Optional[Dict[str, Any]]:
        """Get previous stance from memory."""
        if current_round == 0:
            return None
        for s in reversed(self.stances):
            if (s['thread_id'] == thread_id and 
                s['panelist_name'] == panelist_name and 
                s['round_number'] == current_round - 1):
                return s
        return None
    
    async def get_round_arguments(self, thread_id: str, round_number: int) -> List[Dict[str, Any]]:
        """Get arguments from memory."""
        return [u for u in self.argument_units
                if u['thread_id'] == thread_id and u['round_number'] == round_number]

    async def save_round_scores(self, thread_id: str, round_number: int,
                                scores: Dict[str, Any]) -> None:
        """Save round scores in memory."""
        for panelist_name, score_data in scores.items():
            # Remove existing score for this round/panelist
            self.scores = [s for s in getattr(self, 'scores', [])
                          if not (s['thread_id'] == thread_id and
                                 s['round_number'] == round_number and
                                 s['panelist_name'] == panelist_name)]
            if not hasattr(self, 'scores'):
                self.scores = []
            self.scores.append({
                'thread_id': thread_id,
                'round_number': round_number,
                'panelist_name': panelist_name,
                'round_total': score_data.get('round_total', 0),
                'cumulative_total': score_data.get('cumulative_total', 0),
                'events': score_data.get('events', [])
            })

    async def save_user_vote(self, thread_id: str, round_number: int,
                            panelist_name: str, vote_type: str,
                            points: int) -> None:
        """Record user vote in memory."""
        if not hasattr(self, 'scores'):
            self.scores = []
        for score in self.scores:
            if (score['thread_id'] == thread_id and
                score['round_number'] == round_number and
                score['panelist_name'] == panelist_name):
                score['round_total'] += points
                score['cumulative_total'] += points
                break

    async def get_cumulative_scores(self, thread_id: str) -> Dict[str, int]:
        """Get cumulative scores from memory."""
        if not hasattr(self, 'scores'):
            return {}
        result = {}
        for score in self.scores:
            if score['thread_id'] == thread_id:
                name = score['panelist_name']
                if name not in result or score['cumulative_total'] > result[name]:
                    result[name] = score['cumulative_total']
        return result

    async def get_round_scores(self, thread_id: str, round_number: int) -> Dict[str, Any]:
        """Get round scores from memory."""
        if not hasattr(self, 'scores'):
            return {}
        result = {}
        for score in self.scores:
            if score['thread_id'] == thread_id and score['round_number'] == round_number:
                result[score['panelist_name']] = {
                    'round_total': score['round_total'],
                    'cumulative_total': score['cumulative_total'],
                    'events': score['events']
                }
        return result
