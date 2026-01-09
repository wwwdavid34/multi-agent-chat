"""FastAPI authentication dependencies."""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from auth.jwt_manager import verify_access_token
from auth.models import TokenPayload


# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=True)
optional_security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenPayload:
    """
    FastAPI dependency to extract and verify the current user from JWT token.

    Usage:
        @app.get("/protected")
        async def protected_route(user: TokenPayload = Depends(get_current_user)):
            return {"user_id": user.user_id, "email": user.email}

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        TokenPayload with user_id, email, exp, iat

    Raises:
        HTTPException 401: If token is missing, invalid, or expired
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract token from "Bearer <token>"
    token = credentials.credentials

    # Verify and decode token
    # This will raise HTTPException if invalid
    return verify_access_token(token)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(optional_security),
) -> Optional[TokenPayload]:
    """
    Optional authentication dependency.

    Returns user if authenticated, None otherwise.
    Does not raise exception if no token provided.

    Usage:
        @app.get("/optional-auth")
        async def optional_route(user: Optional[TokenPayload] = Depends(get_current_user_optional)):
            if user:
                return {"message": f"Hello {user.email}"}
            return {"message": "Hello anonymous user"}

    Args:
        credentials: Optional HTTP Bearer token

    Returns:
        TokenPayload if authenticated, None otherwise
    """
    if not credentials:
        return None

    try:
        token = credentials.credentials
        return verify_access_token(token)
    except HTTPException:
        # Token is invalid - return None instead of raising
        return None


async def require_user_id(
    user: TokenPayload = Depends(get_current_user),
) -> str:
    """
    Dependency that returns just the user_id string.

    Usage:
        @app.get("/my-data")
        async def get_my_data(user_id: str = Depends(require_user_id)):
            return await fetch_user_data(user_id)

    Args:
        user: Token payload from get_current_user

    Returns:
        User UUID as string
    """
    return user.user_id


async def require_email(
    user: TokenPayload = Depends(get_current_user),
) -> str:
    """
    Dependency that returns just the user email.

    Usage:
        @app.post("/subscribe")
        async def subscribe(email: str = Depends(require_email)):
            return await add_to_newsletter(email)

    Args:
        user: Token payload from get_current_user

    Returns:
        User email as string
    """
    return user.email


def verify_user_owns_thread(user_id: str, thread_id: str) -> None:
    """
    Verify that a user owns/has access to a specific thread.

    This is a placeholder - actual implementation would query the database.
    Used to prevent users from accessing other users' threads.

    Args:
        user_id: User UUID
        thread_id: Thread identifier

    Raises:
        HTTPException 403: If user doesn't own the thread
    """
    # TODO: Query database to verify user_threads table
    # For now, this is a placeholder that should be implemented
    # when thread endpoints are created
    pass


def verify_user_matches(user: TokenPayload, expected_user_id: str) -> None:
    """
    Verify that the authenticated user matches an expected user_id.

    Useful for endpoints that take a user_id parameter to ensure
    users can only access their own data.

    Args:
        user: Token payload from get_current_user
        expected_user_id: Expected user UUID

    Raises:
        HTTPException 403: If user IDs don't match
    """
    if user.user_id != expected_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own data",
        )
