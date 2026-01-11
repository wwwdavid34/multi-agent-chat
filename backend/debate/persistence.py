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
                    stance TEXT NOT NULL,  -- 'FOR', 'AGAINST', 'CONDITIONAL', 'NEUTRAL'
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
            stance: Position ('FOR', 'AGAINST', 'CONDITIONAL', 'NEUTRAL')
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
