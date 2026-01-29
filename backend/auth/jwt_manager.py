"""JWT token creation and validation."""

import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import HTTPException, status

from auth.models import TokenPayload

logger = logging.getLogger(__name__)


class JWTError(Exception):
    """Custom exception for JWT errors."""

    pass


_secret_logged = False


def get_jwt_secret() -> str:
    """Get JWT secret key from environment."""
    global _secret_logged
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        raise JWTError(
            "JWT_SECRET_KEY environment variable not set. "
            "Generate one with: openssl rand -hex 32"
        )
    if len(secret) < 32:
        raise JWTError(
            "JWT_SECRET_KEY is too short (minimum 32 characters). "
            "Generate a new one with: openssl rand -hex 32"
        )
    if not _secret_logged:
        logger.info("JWT secret key loaded (length=%d)", len(secret))
        _secret_logged = True
    return secret


def create_access_token(
    user_id: str,
    email: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User UUID
        email: User email address
        expires_delta: Token expiration time (default: 7 days)

    Returns:
        Encoded JWT token string

    Raises:
        JWTError: If JWT_SECRET_KEY is not configured
    """
    if expires_delta is None:
        # Default: 7 days
        expires_delta = timedelta(days=7)

    # Use time.time() for correct UTC epoch seconds.
    # datetime.utcnow().timestamp() is WRONG: it returns a naive datetime
    # but .timestamp() interprets it as local time, shifting iat into the future.
    now_epoch = int(time.time())
    expire_epoch = now_epoch + int(expires_delta.total_seconds())

    payload = {
        "user_id": user_id,
        "email": email,
        "exp": expire_epoch,
        "iat": now_epoch,
    }

    try:
        secret = get_jwt_secret()
        encoded_jwt = jwt.encode(payload, secret, algorithm="HS256")
        return encoded_jwt
    except Exception as e:
        raise JWTError(f"Failed to create JWT token: {str(e)}") from e


def verify_access_token(token: str) -> TokenPayload:
    """
    Verify and decode a JWT access token.

    Args:
        token: JWT token string

    Returns:
        TokenPayload with user_id, email, exp, iat

    Raises:
        HTTPException: If token is invalid, expired, or verification fails
    """
    try:
        secret = get_jwt_secret()

        # Decode and verify the token
        # This automatically checks:
        # - Token signature
        # - Token expiration (exp claim)
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            options={"require": ["exp", "iat"]},
            leeway=10,  # 10-second tolerance for clock skew
        )

        # Validate required fields
        if "user_id" not in payload or "email" not in payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: missing required fields",
            )

        # Return validated payload
        return TokenPayload(**payload)

    except jwt.ExpiredSignatureError:
        logger.warning("JWT verify failed: token expired (prefix=%s…)", token[:8])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired. Please log in again.",
        )

    except jwt.InvalidTokenError as e:
        logger.warning("JWT verify failed: invalid token (prefix=%s…): %s", token[:8], e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
        )

    except JWTError as e:
        logger.error("JWT verify failed: config error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    except Exception as e:
        logger.error("JWT verify failed: unexpected error (prefix=%s…): %s", token[:8], e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
        )


def decode_token_unsafe(token: str) -> Optional[dict]:
    """
    Decode a JWT token without verification (for debugging only).

    WARNING: Do NOT use this for authentication - it doesn't verify the signature!

    Args:
        token: JWT token string

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        # Decode without verification
        payload = jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception:
        return None


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Get the expiration time of a token without full verification.

    Args:
        token: JWT token string

    Returns:
        Expiration datetime or None if invalid
    """
    payload = decode_token_unsafe(token)
    if payload and "exp" in payload:
        return datetime.fromtimestamp(payload["exp"])
    return None


def validate_jwt_config() -> dict:
    """
    Validate that JWT is properly configured.

    Returns:
        dict with config status
    """
    secret = os.getenv("JWT_SECRET_KEY")

    if not secret:
        return {
            "configured": False,
            "error": "JWT_SECRET_KEY not set",
            "instructions": "Generate with: openssl rand -hex 32",
        }

    if len(secret) < 32:
        return {
            "configured": False,
            "error": "JWT_SECRET_KEY too short",
            "instructions": "Generate a new one with: openssl rand -hex 32",
        }

    return {
        "configured": True,
        "secret_length": len(secret),
    }
