"""Authentication router with login, user management, and API key storage."""

import json
import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status

from auth.dependencies import get_current_user, require_user_id
from auth.encryption import (
    decrypt_api_keys,
    encrypt_api_keys,
    generate_salt,
    sanitize_api_keys,
)
from auth.google_oauth import verify_google_token
from auth.jwt_manager import create_access_token
from pydantic import BaseModel

from auth.models import (
    ApiKeysRequest,
    ApiKeysResponse,
    GoogleTokenRequest,
    LoginResponse,
    ThreadListResponse,
    ThreadMigrationRequest,
    ThreadMigrationResponse,
    ThreadResponse,
    TokenPayload,
    UserResponse,
)
from config import get_pg_conn_str

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


async def get_db_pool():
    """Get database connection pool."""
    conn_str = get_pg_conn_str()
    return await asyncpg.create_pool(conn_str, min_size=1, max_size=10)


# Global connection pool (will be initialized on first request)
_db_pool: Optional[asyncpg.Pool] = None


async def get_db():
    """Get database connection from pool."""
    global _db_pool
    if _db_pool is None:
        _db_pool = await get_db_pool()
    return _db_pool


@router.post("/google", response_model=LoginResponse)
async def login_with_google(
    request: GoogleTokenRequest,
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Login or register user with Google OAuth token.

    Flow:
    1. Verify Google token
    2. Check if user exists (by google_id)
    3. If new user: create account
    4. If existing user: update last_login
    5. Generate JWT access token
    6. Return token + user info

    Args:
        request: Google ID token from frontend

    Returns:
        LoginResponse with JWT token and user info

    Raises:
        HTTPException 401: If Google token is invalid
    """
    # Verify Google token
    google_user = await verify_google_token(request.token)

    google_id = google_user["sub"]
    email = google_user["email"]
    name = google_user.get("name")
    picture = google_user.get("picture")

    async with pool.acquire() as conn:
        # Check if user exists
        user_row = await conn.fetchrow(
            "SELECT id, google_id, email, name, picture_url, role, created_at, last_login "
            "FROM users WHERE google_id = $1",
            google_id,
        )

        if user_row:
            # Existing user - update last_login
            user_id = str(user_row["id"])
            await conn.execute(
                "UPDATE users SET last_login = NOW() WHERE id = $1",
                user_row["id"],
            )
            logger.info(f"User logged in: {email}")

        else:
            # New user - create account
            user_row = await conn.fetchrow(
                """
                INSERT INTO users (google_id, email, name, picture_url)
                VALUES ($1, $2, $3, $4)
                RETURNING id, google_id, email, name, picture_url, role, created_at, last_login
                """,
                google_id,
                email,
                name,
                picture,
            )
            user_id = str(user_row["id"])
            logger.info(f"New user created: {email}")

        # Generate JWT access token
        access_token = create_access_token(user_id=user_id, email=email)

        # Build response
        user_response = UserResponse(
            id=user_id,
            email=user_row["email"],
            name=user_row["name"],
            picture_url=user_row["picture_url"],
            role=user_row["role"] or "user",
            created_at=user_row["created_at"],
            last_login=user_row["last_login"],
        )

        return LoginResponse(
            access_token=access_token,
            token_type="bearer",
            user=user_response,
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    user: TokenPayload = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Get current authenticated user's information.

    Requires: Valid JWT token in Authorization header

    Returns:
        User information
    """
    async with pool.acquire() as conn:
        user_row = await conn.fetchrow(
            "SELECT id, email, name, picture_url, role, created_at, last_login "
            "FROM users WHERE id = $1",
            UUID(user.user_id),
        )

        if not user_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return UserResponse(
            id=str(user_row["id"]),
            email=user_row["email"],
            name=user_row["name"],
            picture_url=user_row["picture_url"],
            role=user_row["role"] or "user",
            created_at=user_row["created_at"],
            last_login=user_row["last_login"],
        )


@router.post("/keys", status_code=status.HTTP_200_OK)
async def save_api_keys(
    request: ApiKeysRequest,
    user: TokenPayload = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Save encrypted API keys for the current user.

    Keys are encrypted using AES-256-GCM with a per-user derived key.

    Requires: Valid JWT token

    Args:
        request: Dictionary of API keys by provider

    Returns:
        Success message
    """
    user_id = user.user_id

    async with pool.acquire() as conn:
        # Get or create user's encryption salt
        salt_row = await conn.fetchrow(
            "SELECT encryption_salt FROM users WHERE id = $1",
            UUID(user_id),
        )

        if not salt_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        salt = salt_row["encryption_salt"]

        # Generate new salt if user doesn't have one yet
        if not salt:
            salt = generate_salt()

        # Encrypt API keys
        encrypted_keys = encrypt_api_keys(request.keys, user_id, salt)

        # Store encrypted keys and salt
        await conn.execute(
            """
            UPDATE users
            SET encrypted_api_keys = $1, encryption_salt = $2
            WHERE id = $3
            """,
            encrypted_keys,
            salt,
            UUID(user_id),
        )

        logger.info(
            f"API keys saved for user {user.email}: "
            f"{sanitize_api_keys(request.keys)}"
        )

        return {
            "message": "API keys saved successfully",
            "providers": list(request.keys.keys()),
        }


@router.get("/keys", response_model=ApiKeysResponse)
async def get_api_keys(
    user: TokenPayload = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Retrieve decrypted API keys for the current user.

    Requires: Valid JWT token

    Returns:
        Decrypted API keys by provider
    """
    user_id = user.user_id

    async with pool.acquire() as conn:
        keys_row = await conn.fetchrow(
            "SELECT encrypted_api_keys, encryption_salt FROM users WHERE id = $1",
            UUID(user_id),
        )

        if not keys_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        encrypted_keys = keys_row["encrypted_api_keys"]
        salt = keys_row["encryption_salt"]

        if not encrypted_keys or not salt:
            # No keys stored yet
            return ApiKeysResponse(keys={})

        # Decrypt keys
        decrypted_keys = decrypt_api_keys(encrypted_keys, user_id, salt)

        logger.info(
            f"API keys retrieved for user {user.email}: "
            f"{sanitize_api_keys(decrypted_keys)}"
        )

        return ApiKeysResponse(keys=decrypted_keys)


@router.post("/migrate-threads", response_model=ThreadMigrationResponse)
async def migrate_threads(
    request: ThreadMigrationRequest,
    user: TokenPayload = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Migrate localStorage threads to user account.

    This is called on first login to claim threads that were created
    anonymously in the browser's localStorage.

    Requires: Valid JWT token

    Args:
        request: List of thread IDs to claim

    Returns:
        Migration results with count of threads migrated
    """
    user_id = user.user_id
    migrated = []
    skipped = 0

    async with pool.acquire() as conn:
        for thread_id in request.thread_ids:
            # Check if thread already exists for this user
            exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM user_threads WHERE user_id = $1 AND thread_id = $2)",
                UUID(user_id),
                thread_id,
            )

            if exists:
                skipped += 1
                continue

            # Create thread ownership record
            await conn.execute(
                """
                INSERT INTO user_threads (user_id, thread_id)
                VALUES ($1, $2)
                ON CONFLICT (user_id, thread_id) DO NOTHING
                """,
                UUID(user_id),
                thread_id,
            )

            # Log migration for audit trail
            metadata_json = json.dumps(request.metadata) if request.metadata else None
            await conn.execute(
                """
                INSERT INTO thread_migrations (user_id, thread_id, source_metadata)
                VALUES ($1, $2, $3)
                """,
                UUID(user_id),
                thread_id,
                metadata_json,
            )

            migrated.append(thread_id)

    logger.info(
        f"Thread migration for {user.email}: "
        f"{len(migrated)} migrated, {skipped} skipped"
    )

    return ThreadMigrationResponse(
        migrated_count=len(migrated),
        thread_ids=migrated,
        skipped_count=skipped,
    )


@router.get("/threads", response_model=ThreadListResponse)
async def list_user_threads(
    user_id: str = Depends(require_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    List all threads owned by the current user.

    Requires: Valid JWT token

    Returns:
        List of user's threads with metadata
    """
    async with pool.acquire() as conn:
        thread_rows = await conn.fetch(
            """
            SELECT thread_id, title, created_at, updated_at
            FROM user_threads
            WHERE user_id = $1
            ORDER BY updated_at DESC
            """,
            UUID(user_id),
        )

        threads = [
            ThreadResponse(
                thread_id=row["thread_id"],
                title=row["title"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in thread_rows
        ]

        return ThreadListResponse(
            threads=threads,
            total=len(threads),
        )


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_thread(
    thread_id: str,
    user_id: str = Depends(require_user_id),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Delete a thread owned by the current user.

    This only removes the ownership record - the actual conversation data
    in LangGraph checkpoints remains (for potential recovery).

    Requires: Valid JWT token

    Args:
        thread_id: Thread identifier to delete

    Returns:
        204 No Content on success

    Raises:
        HTTPException 404: If thread doesn't exist or user doesn't own it
    """
    async with pool.acquire() as conn:
        result = await conn.execute(
            "DELETE FROM user_threads WHERE user_id = $1 AND thread_id = $2",
            UUID(user_id),
            thread_id,
        )

        # Check if anything was deleted
        if result == "DELETE 0":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Thread not found or you don't have permission to delete it",
            )

        logger.info(f"Thread deleted: {thread_id} by user {user_id}")


# ============================================================================
# System Key Status
# ============================================================================


class SystemKeyStatusResponse(BaseModel):
    """Response showing which providers user can access via system keys."""

    openai: bool = False
    anthropic: bool = False
    google: bool = False
    xai: bool = False


@router.get("/system-key-status", response_model=SystemKeyStatusResponse)
async def get_system_key_status(
    user: TokenPayload = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Check which providers the current user can access via system keys.

    Returns a map of provider -> boolean indicating if the user is allowlisted
    for that provider's system key.

    Requires: Valid JWT token
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT provider FROM system_key_allowlist WHERE email = $1",
            user.email,
        )

        providers = {row["provider"] for row in rows}

        return SystemKeyStatusResponse(
            openai="openai" in providers,
            anthropic="anthropic" in providers,
            google="google" in providers,
            xai="xai" in providers,
        )
