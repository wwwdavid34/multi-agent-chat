"""Conversation message persistence endpoints.

Replaces localStorage-based message storage with server-side persistence.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional, Union
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from auth.dependencies import require_user_id
from config import get_pg_conn_str

logger = logging.getLogger(__name__)


def safe_json_parse(value: Any, default: Any = None) -> Any:
    """Safely parse JSON data that might be a string or already parsed.

    asyncpg may return JSONB as either parsed Python objects or raw strings
    depending on configuration. This handles both cases.
    """
    if value is None:
        return default
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            logger.warning(f"Failed to parse JSON string: {value[:100] if len(value) > 100 else value}")
            return default
    # Already parsed (dict, list, etc.)
    return value

router = APIRouter(prefix="/conversations", tags=["Conversations"])


# Global connection pool
_db_pool: Optional[asyncpg.Pool] = None


async def get_db():
    """Get database connection from pool."""
    global _db_pool
    if _db_pool is None:
        conn_str = get_pg_conn_str()
        _db_pool = await asyncpg.create_pool(conn_str, min_size=1, max_size=10)
        # Ensure table exists
        async with _db_pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_messages (
                    id SERIAL PRIMARY KEY,
                    thread_id VARCHAR(255) NOT NULL,
                    user_id UUID NOT NULL,
                    message_id VARCHAR(255) NOT NULL,
                    question TEXT NOT NULL,
                    attachments JSONB DEFAULT '[]',
                    summary TEXT,
                    panel_responses JSONB DEFAULT '{}',
                    panelists JSONB DEFAULT '[]',
                    debate_history JSONB,
                    debate_mode VARCHAR(50),
                    max_debate_rounds INT,
                    debate_paused BOOLEAN DEFAULT FALSE,
                    stopped BOOLEAN DEFAULT FALSE,
                    usage JSONB,
                    tagged_panelists JSONB DEFAULT '[]',
                    created_at TIMESTAMP DEFAULT NOW(),
                    updated_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(thread_id, message_id)
                )
            """)
    return _db_pool


# ============================================================================
# Request/Response Models
# ============================================================================


class PanelistConfig(BaseModel):
    """Panelist configuration."""
    id: str
    name: str
    provider: str
    model: str
    role: Optional[str] = None


class TokenUsage(BaseModel):
    """Token usage statistics."""
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0
    call_count: Optional[int] = None


class DebateRound(BaseModel):
    """A single round of debate."""
    round_number: int
    panel_responses: dict[str, str]
    consensus_reached: bool = False
    user_message: Optional[str] = None
    stances: Optional[dict[str, Any]] = None
    scores: Optional[dict[str, Any]] = None


class MessageEntry(BaseModel):
    """A single conversation message entry."""
    id: str = Field(..., description="Unique message ID")
    question: str = Field(..., description="User's question")
    attachments: list[str] = Field(default_factory=list)
    summary: Optional[str] = None
    panel_responses: dict[str, str] = Field(default_factory=dict)
    panelists: list[PanelistConfig] = Field(default_factory=list)
    debate_history: Optional[list[DebateRound]] = None
    debate_mode: Optional[str] = None
    max_debate_rounds: Optional[int] = None
    debate_paused: bool = False
    stopped: bool = False
    usage: Optional[TokenUsage] = None
    tagged_panelists: Optional[list[str]] = None


class SaveMessageRequest(BaseModel):
    """Request to save a single message."""
    thread_id: str
    message: MessageEntry


class SaveMessagesRequest(BaseModel):
    """Request to save multiple messages (batch)."""
    thread_id: str
    messages: list[MessageEntry]


class ConversationResponse(BaseModel):
    """Response with conversation messages."""
    thread_id: str
    messages: list[MessageEntry]


class ThreadsConversationsResponse(BaseModel):
    """Response with multiple thread conversations."""
    conversations: dict[str, list[MessageEntry]]


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/{thread_id}/messages", status_code=status.HTTP_201_CREATED)
async def save_message(
    thread_id: str,
    request: SaveMessageRequest,
    user_id: str = Depends(require_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Save a single conversation message.

    Creates or updates a message in the conversation.
    """
    msg = request.message

    async with pool.acquire() as conn:
        # Ensure user_threads entry exists
        await conn.execute(
            """
            INSERT INTO user_threads (user_id, thread_id, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (user_id, thread_id) DO UPDATE SET updated_at = NOW()
            """,
            UUID(user_id),
            thread_id,
        )

        # Upsert the message
        await conn.execute(
            """
            INSERT INTO conversation_messages (
                thread_id, user_id, message_id, question, attachments,
                summary, panel_responses, panelists, debate_history,
                debate_mode, max_debate_rounds, debate_paused, stopped,
                usage, tagged_panelists
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            ON CONFLICT (thread_id, message_id) DO UPDATE SET
                question = EXCLUDED.question,
                attachments = EXCLUDED.attachments,
                summary = EXCLUDED.summary,
                panel_responses = EXCLUDED.panel_responses,
                panelists = EXCLUDED.panelists,
                debate_history = EXCLUDED.debate_history,
                debate_mode = EXCLUDED.debate_mode,
                max_debate_rounds = EXCLUDED.max_debate_rounds,
                debate_paused = EXCLUDED.debate_paused,
                stopped = EXCLUDED.stopped,
                usage = EXCLUDED.usage,
                tagged_panelists = EXCLUDED.tagged_panelists,
                updated_at = NOW()
            """,
            thread_id,
            UUID(user_id),
            msg.id,
            msg.question,
            json.dumps(msg.attachments),
            msg.summary,
            json.dumps(msg.panel_responses),
            json.dumps([p.model_dump() for p in msg.panelists]),
            json.dumps([r.model_dump() for r in msg.debate_history]) if msg.debate_history else None,
            msg.debate_mode,
            msg.max_debate_rounds,
            msg.debate_paused,
            msg.stopped,
            json.dumps(msg.usage.model_dump()) if msg.usage else None,
            json.dumps(msg.tagged_panelists) if msg.tagged_panelists else None,
        )

    logger.info(f"Saved message {msg.id} to thread {thread_id} for user {user_id}")
    return {"status": "ok", "message_id": msg.id}


@router.post("/{thread_id}/messages/batch", status_code=status.HTTP_201_CREATED)
async def save_messages_batch(
    thread_id: str,
    request: SaveMessagesRequest,
    user_id: str = Depends(require_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Save multiple messages in a batch.

    Useful for initial migration or bulk updates.
    """
    async with pool.acquire() as conn:
        # Ensure user_threads entry exists
        await conn.execute(
            """
            INSERT INTO user_threads (user_id, thread_id, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (user_id, thread_id) DO UPDATE SET updated_at = NOW()
            """,
            UUID(user_id),
            thread_id,
        )

        for msg in request.messages:
            await conn.execute(
                """
                INSERT INTO conversation_messages (
                    thread_id, user_id, message_id, question, attachments,
                    summary, panel_responses, panelists, debate_history,
                    debate_mode, max_debate_rounds, debate_paused, stopped,
                    usage, tagged_panelists
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (thread_id, message_id) DO UPDATE SET
                    question = EXCLUDED.question,
                    attachments = EXCLUDED.attachments,
                    summary = EXCLUDED.summary,
                    panel_responses = EXCLUDED.panel_responses,
                    panelists = EXCLUDED.panelists,
                    debate_history = EXCLUDED.debate_history,
                    debate_mode = EXCLUDED.debate_mode,
                    max_debate_rounds = EXCLUDED.max_debate_rounds,
                    debate_paused = EXCLUDED.debate_paused,
                    stopped = EXCLUDED.stopped,
                    usage = EXCLUDED.usage,
                    tagged_panelists = EXCLUDED.tagged_panelists,
                    updated_at = NOW()
                """,
                thread_id,
                UUID(user_id),
                msg.id,
                msg.question,
                json.dumps(msg.attachments),
                msg.summary,
                json.dumps(msg.panel_responses),
                json.dumps([p.model_dump() for p in msg.panelists]),
                json.dumps([r.model_dump() for r in msg.debate_history]) if msg.debate_history else None,
                msg.debate_mode,
                msg.max_debate_rounds,
                msg.debate_paused,
                msg.stopped,
                json.dumps(msg.usage.model_dump()) if msg.usage else None,
                json.dumps(msg.tagged_panelists) if msg.tagged_panelists else None,
            )

    logger.info(f"Saved {len(request.messages)} messages to thread {thread_id}")
    return {"status": "ok", "count": len(request.messages)}


@router.get("/{thread_id}", response_model=ConversationResponse)
async def get_conversation(
    thread_id: str,
    user_id: str = Depends(require_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Get all messages for a conversation thread.

    Returns messages in chronological order.
    """
    async with pool.acquire() as conn:
        # Verify user owns this thread
        owns = await conn.fetchval(
            "SELECT EXISTS(SELECT 1 FROM user_threads WHERE user_id = $1 AND thread_id = $2)",
            UUID(user_id),
            thread_id,
        )

        if not owns:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or you don't have access",
            )

        rows = await conn.fetch(
            """
            SELECT message_id, question, attachments, summary, panel_responses,
                   panelists, debate_history, debate_mode, max_debate_rounds,
                   debate_paused, stopped, usage, tagged_panelists, created_at
            FROM conversation_messages
            WHERE thread_id = $1 AND user_id = $2
            ORDER BY created_at ASC
            """,
            thread_id,
            UUID(user_id),
        )

        messages = []
        for row in rows:
            try:
                # Parse JSONB fields with safe parsing
                attachments = safe_json_parse(row["attachments"], [])
                panel_responses = safe_json_parse(row["panel_responses"], {})
                panelists_data = safe_json_parse(row["panelists"], [])
                debate_history_data = safe_json_parse(row["debate_history"], None)
                usage_data = safe_json_parse(row["usage"], None)
                tagged = safe_json_parse(row["tagged_panelists"], [])

                # Convert to model objects with validation
                panelists = []
                for p in panelists_data:
                    if isinstance(p, dict):
                        try:
                            panelists.append(PanelistConfig(**p))
                        except Exception as e:
                            logger.warning(f"Failed to parse panelist config: {p}, error: {e}")

                debate_history = None
                if debate_history_data and isinstance(debate_history_data, list):
                    debate_history = []
                    for r in debate_history_data:
                        if isinstance(r, dict):
                            try:
                                debate_history.append(DebateRound(**r))
                            except Exception as e:
                                logger.warning(f"Failed to parse debate round: {e}")

                usage = None
                if usage_data and isinstance(usage_data, dict):
                    try:
                        usage = TokenUsage(**usage_data)
                    except Exception as e:
                        logger.warning(f"Failed to parse usage data: {e}")

                messages.append(MessageEntry(
                    id=row["message_id"],
                    question=row["question"],
                    attachments=attachments if isinstance(attachments, list) else [],
                    summary=row["summary"],
                    panel_responses=panel_responses if isinstance(panel_responses, dict) else {},
                    panelists=panelists,
                    debate_history=debate_history,
                    debate_mode=row["debate_mode"],
                    max_debate_rounds=row["max_debate_rounds"],
                    debate_paused=row["debate_paused"] or False,
                    stopped=row["stopped"] or False,
                    usage=usage,
                    tagged_panelists=tagged if isinstance(tagged, list) else [],
                ))
            except Exception as e:
                logger.error(f"Failed to parse message row: {e}")
                # Continue with other messages

        return ConversationResponse(thread_id=thread_id, messages=messages)


@router.get("/", response_model=ThreadsConversationsResponse)
async def get_all_conversations(
    user_id: str = Depends(require_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Get all conversations for the current user.

    Returns a map of thread_id -> messages.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT thread_id, message_id, question, attachments, summary, panel_responses,
                   panelists, debate_history, debate_mode, max_debate_rounds,
                   debate_paused, stopped, usage, tagged_panelists, created_at
            FROM conversation_messages
            WHERE user_id = $1
            ORDER BY thread_id, created_at ASC
            """,
            UUID(user_id),
        )

        conversations: dict[str, list[MessageEntry]] = {}

        for row in rows:
            thread_id = row["thread_id"]
            if thread_id not in conversations:
                conversations[thread_id] = []

            try:
                # Parse JSONB fields with safe parsing (handles both string and parsed data)
                attachments = safe_json_parse(row["attachments"], [])
                panel_responses = safe_json_parse(row["panel_responses"], {})
                panelists_data = safe_json_parse(row["panelists"], [])
                debate_history_data = safe_json_parse(row["debate_history"], None)
                usage_data = safe_json_parse(row["usage"], None)
                tagged = safe_json_parse(row["tagged_panelists"], [])

                # Parse panelists with validation
                panelists = []
                for p in panelists_data:
                    if isinstance(p, dict):
                        try:
                            panelists.append(PanelistConfig(**p))
                        except Exception as e:
                            logger.warning(f"Failed to parse panelist config: {p}, error: {e}")
                    else:
                        logger.warning(f"Unexpected panelist data type: {type(p)}, value: {p}")

                # Parse debate history with validation
                debate_history = None
                if debate_history_data and isinstance(debate_history_data, list):
                    debate_history = []
                    for r in debate_history_data:
                        if isinstance(r, dict):
                            try:
                                debate_history.append(DebateRound(**r))
                            except Exception as e:
                                logger.warning(f"Failed to parse debate round: {e}")

                # Parse usage with validation
                usage = None
                if usage_data and isinstance(usage_data, dict):
                    try:
                        usage = TokenUsage(**usage_data)
                    except Exception as e:
                        logger.warning(f"Failed to parse usage data: {e}")

                conversations[thread_id].append(MessageEntry(
                    id=row["message_id"],
                    question=row["question"],
                    attachments=attachments if isinstance(attachments, list) else [],
                    summary=row["summary"],
                    panel_responses=panel_responses if isinstance(panel_responses, dict) else {},
                    panelists=panelists,
                    debate_history=debate_history,
                    debate_mode=row["debate_mode"],
                    max_debate_rounds=row["max_debate_rounds"],
                    debate_paused=row["debate_paused"] or False,
                    stopped=row["stopped"] or False,
                    usage=usage,
                    tagged_panelists=tagged if isinstance(tagged, list) else [],
                ))
            except Exception as e:
                logger.error(f"Failed to parse message row for thread {thread_id}: {e}")
                # Continue with other messages

        return ThreadsConversationsResponse(conversations=conversations)


@router.delete("/{thread_id}/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    thread_id: str,
    message_id: str,
    user_id: str = Depends(require_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    """Delete a specific message from a conversation."""
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            DELETE FROM conversation_messages
            WHERE thread_id = $1 AND message_id = $2 AND user_id = $3
            """,
            thread_id,
            message_id,
            UUID(user_id),
        )

        if result == "DELETE 0":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Message not found or you don't have permission",
            )

    logger.info(f"Deleted message {message_id} from thread {thread_id}")


@router.delete("/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    thread_id: str,
    user_id: str = Depends(require_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    """Delete all messages in a conversation."""
    async with pool.acquire() as conn:
        # Delete messages
        await conn.execute(
            """
            DELETE FROM conversation_messages
            WHERE thread_id = $1 AND user_id = $2
            """,
            thread_id,
            UUID(user_id),
        )

        # Also delete the thread ownership record
        await conn.execute(
            """
            DELETE FROM user_threads
            WHERE thread_id = $1 AND user_id = $2
            """,
            thread_id,
            UUID(user_id),
        )

    logger.info(f"Deleted conversation {thread_id} for user {user_id}")
