"""Admin router for system key allowlist management."""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import asyncpg
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from auth.dependencies import get_current_user
from auth.models import TokenPayload
from routers.auth import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/admin", tags=["Admin"])


# ============================================================================
# Models
# ============================================================================


class AllowlistEntry(BaseModel):
    """System key allowlist entry."""

    id: int
    email: str
    provider: str
    added_by: str
    notes: Optional[str] = None
    created_at: datetime


class AllowlistCreateRequest(BaseModel):
    """Request to add email to allowlist."""

    email: EmailStr = Field(..., description="Email address to allowlist")
    provider: str = Field(
        ...,
        description="Provider name",
        pattern="^(openai|anthropic|google|xai)$",
    )
    notes: Optional[str] = Field(None, description="Optional notes")


class AllowlistResponse(BaseModel):
    """Response with allowlist entries."""

    entries: List[AllowlistEntry]
    total: int


class UserWithRole(BaseModel):
    """User info with role."""

    id: str
    email: str
    name: Optional[str]
    role: str
    created_at: datetime
    last_login: datetime


class UsersListResponse(BaseModel):
    """List of users with roles."""

    users: List[UserWithRole]
    total: int


class UpdateRoleRequest(BaseModel):
    """Request to update user role."""

    role: str = Field(..., pattern="^(user|admin)$", description="New role")


class SystemKeyStatusResponse(BaseModel):
    """Response showing which providers user can access via system keys."""

    openai: bool = False
    anthropic: bool = False
    google: bool = False
    xai: bool = False


# ============================================================================
# Dependencies
# ============================================================================


async def require_admin(
    user: TokenPayload = Depends(get_current_user),
    pool: asyncpg.Pool = Depends(get_db),
) -> TokenPayload:
    """
    Dependency that requires admin role.

    Raises HTTPException 403 if user is not an admin.
    """
    async with pool.acquire() as conn:
        role = await conn.fetchval(
            "SELECT role FROM users WHERE id = $1",
            UUID(user.user_id),
        )

        if role != "admin":
            logger.warning(f"Non-admin user {user.email} attempted admin action")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin access required",
            )

    return user


# ============================================================================
# Allowlist Endpoints
# ============================================================================


@router.get("/allowlist", response_model=AllowlistResponse)
async def list_allowlist(
    admin: TokenPayload = Depends(require_admin),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    List all system key allowlist entries.

    Requires: Admin role
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, email, provider, added_by, notes, created_at
            FROM system_key_allowlist
            ORDER BY created_at DESC
            """
        )

        entries = [
            AllowlistEntry(
                id=row["id"],
                email=row["email"],
                provider=row["provider"],
                added_by=row["added_by"],
                notes=row["notes"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

        return AllowlistResponse(entries=entries, total=len(entries))


@router.post("/allowlist", response_model=AllowlistEntry, status_code=status.HTTP_201_CREATED)
async def add_to_allowlist(
    request: AllowlistCreateRequest,
    admin: TokenPayload = Depends(require_admin),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Add an email to the system key allowlist for a provider.

    Requires: Admin role

    Args:
        request: Email and provider to allowlist
    """
    async with pool.acquire() as conn:
        # Check if entry already exists
        existing = await conn.fetchval(
            "SELECT id FROM system_key_allowlist WHERE email = $1 AND provider = $2",
            request.email,
            request.provider,
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"{request.email} is already allowlisted for {request.provider}",
            )

        # Insert new entry
        row = await conn.fetchrow(
            """
            INSERT INTO system_key_allowlist (email, provider, added_by, notes)
            VALUES ($1, $2, $3, $4)
            RETURNING id, email, provider, added_by, notes, created_at
            """,
            request.email,
            request.provider,
            admin.email,
            request.notes,
        )

        # Audit log
        await conn.execute(
            """
            INSERT INTO system_key_audit (user_email, provider, action, metadata)
            VALUES ($1, $2, $3, $4)
            """,
            request.email,
            request.provider,
            "allowlist_added",
            {"added_by": admin.email, "notes": request.notes},
        )

        logger.info(f"Admin {admin.email} added {request.email} to {request.provider} allowlist")

        return AllowlistEntry(
            id=row["id"],
            email=row["email"],
            provider=row["provider"],
            added_by=row["added_by"],
            notes=row["notes"],
            created_at=row["created_at"],
        )


@router.delete("/allowlist/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_allowlist(
    entry_id: int,
    admin: TokenPayload = Depends(require_admin),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Remove an entry from the system key allowlist.

    Requires: Admin role

    Args:
        entry_id: ID of the allowlist entry to remove
    """
    async with pool.acquire() as conn:
        # Get entry details for audit
        entry = await conn.fetchrow(
            "SELECT email, provider FROM system_key_allowlist WHERE id = $1",
            entry_id,
        )

        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Allowlist entry not found",
            )

        # Delete entry
        await conn.execute(
            "DELETE FROM system_key_allowlist WHERE id = $1",
            entry_id,
        )

        # Audit log
        await conn.execute(
            """
            INSERT INTO system_key_audit (user_email, provider, action, metadata)
            VALUES ($1, $2, $3, $4)
            """,
            entry["email"],
            entry["provider"],
            "allowlist_removed",
            {"removed_by": admin.email},
        )

        logger.info(
            f"Admin {admin.email} removed {entry['email']} from {entry['provider']} allowlist"
        )


# ============================================================================
# User Management Endpoints
# ============================================================================


@router.get("/users", response_model=UsersListResponse)
async def list_users(
    admin: TokenPayload = Depends(require_admin),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    List all users with their roles.

    Requires: Admin role
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT id, email, name, role, created_at, last_login
            FROM users
            ORDER BY created_at DESC
            """
        )

        users = [
            UserWithRole(
                id=str(row["id"]),
                email=row["email"],
                name=row["name"],
                role=row["role"] or "user",
                created_at=row["created_at"],
                last_login=row["last_login"],
            )
            for row in rows
        ]

        return UsersListResponse(users=users, total=len(users))


@router.put("/users/{user_id}/role", response_model=UserWithRole)
async def update_user_role(
    user_id: str,
    request: UpdateRoleRequest,
    admin: TokenPayload = Depends(require_admin),
    pool: asyncpg.Pool = Depends(get_db),
):
    """
    Update a user's role.

    Requires: Admin role

    Args:
        user_id: UUID of user to update
        request: New role
    """
    # Prevent admin from removing their own admin role
    if user_id == admin.user_id and request.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove your own admin role",
        )

    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE users
            SET role = $1
            WHERE id = $2
            RETURNING id, email, name, role, created_at, last_login
            """,
            request.role,
            UUID(user_id),
        )

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        logger.info(f"Admin {admin.email} changed role of {row['email']} to {request.role}")

        return UserWithRole(
            id=str(row["id"]),
            email=row["email"],
            name=row["name"],
            role=row["role"],
            created_at=row["created_at"],
            last_login=row["last_login"],
        )
