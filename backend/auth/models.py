"""Pydantic models for authentication."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class GoogleTokenRequest(BaseModel):
    """Request body for Google OAuth token verification."""

    token: str = Field(..., description="Google ID token from frontend")


class UserCreate(BaseModel):
    """User creation data from Google OAuth."""

    google_id: str = Field(..., description="Google sub (unique identifier)")
    email: EmailStr = Field(..., description="User email address")
    name: Optional[str] = Field(None, description="User display name")
    picture_url: Optional[str] = Field(None, description="User profile picture URL")


class UserResponse(BaseModel):
    """User data returned to frontend."""

    id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email address")
    name: Optional[str] = Field(None, description="User display name")
    picture_url: Optional[str] = Field(None, description="Profile picture URL")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login: datetime = Field(..., description="Last login timestamp")


class LoginResponse(BaseModel):
    """Response after successful login."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    user: UserResponse = Field(..., description="User information")


class TokenPayload(BaseModel):
    """JWT token payload structure."""

    user_id: str = Field(..., description="User UUID")
    email: str = Field(..., description="User email")
    exp: int = Field(..., description="Expiration timestamp")
    iat: int = Field(..., description="Issued at timestamp")


class ApiKeysRequest(BaseModel):
    """Request to save API keys."""

    keys: dict[str, str] = Field(
        ...,
        description="API keys by provider",
        example={
            "openai": "sk-...",
            "anthropic": "sk-ant-...",
            "google": "...",
        },
    )


class ApiKeysResponse(BaseModel):
    """Response with decrypted API keys."""

    keys: dict[str, str] = Field(..., description="Decrypted API keys by provider")


class ThreadMigrationRequest(BaseModel):
    """Request to migrate localStorage threads to user account."""

    thread_ids: list[str] = Field(..., description="List of thread IDs to claim")
    metadata: Optional[dict] = Field(
        None, description="Optional metadata from localStorage"
    )


class ThreadMigrationResponse(BaseModel):
    """Response after thread migration."""

    migrated_count: int = Field(..., description="Number of threads migrated")
    thread_ids: list[str] = Field(..., description="Successfully migrated thread IDs")
    skipped_count: int = Field(
        default=0, description="Number of threads skipped (already existed)"
    )


class ThreadResponse(BaseModel):
    """Thread information for user."""

    thread_id: str = Field(..., description="Thread identifier")
    title: Optional[str] = Field(None, description="Thread title")
    created_at: datetime = Field(..., description="Thread creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


class ThreadListResponse(BaseModel):
    """List of user threads."""

    threads: list[ThreadResponse] = Field(..., description="User's threads")
    total: int = Field(..., description="Total number of threads")
