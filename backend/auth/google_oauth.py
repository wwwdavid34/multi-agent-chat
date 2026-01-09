"""Google OAuth token verification."""

import os
from typing import Optional

from google.auth.transport import requests
from google.oauth2 import id_token
from fastapi import HTTPException, status


class GoogleOAuthError(Exception):
    """Custom exception for Google OAuth errors."""

    pass


def get_google_client_id() -> str:
    """Get Google OAuth client ID from environment."""
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise GoogleOAuthError(
            "GOOGLE_CLIENT_ID environment variable not set. "
            "Please configure Google OAuth credentials."
        )
    return client_id


async def verify_google_token(token: str) -> dict:
    """
    Verify Google ID token and return user information.

    Args:
        token: Google ID token from frontend

    Returns:
        dict with user info: {
            "sub": google_id,
            "email": email,
            "name": name,
            "picture": picture_url,
            "email_verified": bool
        }

    Raises:
        HTTPException: If token is invalid or verification fails
    """
    try:
        # Get configured client ID
        client_id = get_google_client_id()

        # Verify the token using Google's library
        # This validates:
        # - Token signature
        # - Token expiration
        # - Token audience (client_id)
        # - Token issuer (accounts.google.com)
        idinfo = id_token.verify_oauth2_token(
            token, requests.Request(), client_id
        )

        # Validate that the token is for our app
        if idinfo["aud"] != client_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token was not issued for this application",
            )

        # Check if email is verified
        if not idinfo.get("email_verified", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email not verified by Google",
            )

        # Return user info
        return {
            "sub": idinfo["sub"],  # Google's unique user identifier
            "email": idinfo["email"],
            "name": idinfo.get("name"),
            "picture": idinfo.get("picture"),
            "email_verified": idinfo.get("email_verified", False),
        }

    except ValueError as e:
        # Token is invalid or expired
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Google token: {str(e)}",
        ) from e

    except Exception as e:
        # Catch any other errors (network issues, etc.)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Token verification failed: {str(e)}",
        ) from e


def validate_google_oauth_config() -> dict:
    """
    Validate that Google OAuth is properly configured.

    Returns:
        dict with config status

    Raises:
        GoogleOAuthError: If configuration is invalid
    """
    client_id = os.getenv("GOOGLE_CLIENT_ID")

    if not client_id:
        return {
            "configured": False,
            "error": "GOOGLE_CLIENT_ID not set",
            "instructions": "Set GOOGLE_CLIENT_ID in your .env file",
        }

    if not client_id.endswith(".apps.googleusercontent.com"):
        return {
            "configured": False,
            "error": "GOOGLE_CLIENT_ID format invalid",
            "instructions": "Should end with .apps.googleusercontent.com",
        }

    return {
        "configured": True,
        "client_id_prefix": client_id.split("-")[0] + "-...",
    }
