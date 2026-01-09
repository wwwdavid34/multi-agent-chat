"""API key encryption and decryption using AES-256-GCM."""

import base64
import json
import os
from typing import Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import HTTPException, status


class EncryptionError(Exception):
    """Custom exception for encryption errors."""

    pass


def get_master_key() -> bytes:
    """
    Get encryption master key from environment.

    Returns:
        32-byte master key

    Raises:
        EncryptionError: If key is not configured or invalid
    """
    key_b64 = os.getenv("ENCRYPTION_MASTER_KEY")
    if not key_b64:
        raise EncryptionError(
            "ENCRYPTION_MASTER_KEY environment variable not set. "
            "Generate one with: python -c 'import os, base64; "
            "print(base64.b64encode(os.urandom(32)).decode())'"
        )

    try:
        key = base64.b64decode(key_b64)
        if len(key) != 32:
            raise EncryptionError(
                f"ENCRYPTION_MASTER_KEY must be 32 bytes (256 bits), got {len(key)}"
            )
        return key
    except Exception as e:
        raise EncryptionError(
            f"Invalid ENCRYPTION_MASTER_KEY format: {str(e)}"
        ) from e


def generate_salt() -> bytes:
    """Generate a random 32-byte salt for key derivation."""
    return os.urandom(32)


def derive_key(master_key: bytes, salt: bytes, user_id: str) -> bytes:
    """
    Derive a user-specific encryption key using PBKDF2.

    Args:
        master_key: 32-byte master encryption key
        salt: 32-byte random salt (stored per-user)
        user_id: User UUID as string (used as additional context)

    Returns:
        32-byte derived key for AES-256-GCM

    Security:
        - Each user gets a unique derived key
        - Salt prevents rainbow table attacks
        - High iteration count (600,000) prevents brute force
        - User ID as context ensures keys are user-specific
    """
    # Combine user_id with master key for additional entropy
    info = user_id.encode("utf-8")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,  # 256 bits for AES-256
        salt=salt,
        iterations=600000,  # OWASP recommendation (2023)
    )

    # Derive key from master_key + user_id
    derived_key = kdf.derive(master_key + info)
    return derived_key


def encrypt_api_keys(keys: dict, user_id: str, salt: bytes) -> str:
    """
    Encrypt API keys using AES-256-GCM.

    Args:
        keys: Dictionary of API keys (provider -> key)
        user_id: User UUID
        salt: User's encryption salt

    Returns:
        Base64-encoded ciphertext (nonce + ciphertext + tag)

    Raises:
        EncryptionError: If encryption fails
    """
    try:
        # Get master key and derive user-specific key
        master_key = get_master_key()
        derived_key = derive_key(master_key, salt, user_id)

        # Initialize AES-GCM cipher
        aesgcm = AESGCM(derived_key)

        # Generate random nonce (12 bytes for GCM)
        nonce = os.urandom(12)

        # Serialize keys to JSON
        plaintext = json.dumps(keys).encode("utf-8")

        # Encrypt with authenticated encryption (AES-256-GCM)
        # This provides both confidentiality and authenticity
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # Combine nonce + ciphertext for storage
        # Format: [12-byte nonce][ciphertext + 16-byte auth tag]
        combined = nonce + ciphertext

        # Encode to base64 for database storage
        return base64.b64encode(combined).decode("utf-8")

    except Exception as e:
        raise EncryptionError(f"Failed to encrypt API keys: {str(e)}") from e


def decrypt_api_keys(
    encrypted_data: str, user_id: str, salt: bytes
) -> dict[str, str]:
    """
    Decrypt API keys using AES-256-GCM.

    Args:
        encrypted_data: Base64-encoded encrypted keys
        user_id: User UUID
        salt: User's encryption salt

    Returns:
        Dictionary of decrypted API keys

    Raises:
        HTTPException: If decryption fails (wrong key, tampered data, etc.)
    """
    try:
        # Get master key and derive user-specific key
        master_key = get_master_key()
        derived_key = derive_key(master_key, salt, user_id)

        # Initialize AES-GCM cipher
        aesgcm = AESGCM(derived_key)

        # Decode from base64
        combined = base64.b64decode(encrypted_data)

        # Extract nonce and ciphertext
        nonce = combined[:12]
        ciphertext = combined[12:]

        # Decrypt and verify authentication tag
        # This will raise an exception if data was tampered with
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)

        # Deserialize JSON
        keys = json.loads(plaintext.decode("utf-8"))

        if not isinstance(keys, dict):
            raise ValueError("Decrypted data is not a dictionary")

        return keys

    except Exception as e:
        # Don't expose internal errors to client
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to decrypt API keys. Keys may be corrupted.",
        ) from e


def validate_encryption_config() -> dict:
    """
    Validate that encryption is properly configured.

    Returns:
        dict with config status
    """
    key_b64 = os.getenv("ENCRYPTION_MASTER_KEY")

    if not key_b64:
        return {
            "configured": False,
            "error": "ENCRYPTION_MASTER_KEY not set",
            "instructions": (
                "Generate with: python -c 'import os, base64; "
                "print(base64.b64encode(os.urandom(32)).decode())'"
            ),
        }

    try:
        key = base64.b64decode(key_b64)
        if len(key) != 32:
            return {
                "configured": False,
                "error": f"Key is {len(key)} bytes, expected 32",
                "instructions": "Generate a new 32-byte key",
            }

        return {
            "configured": True,
            "key_length": len(key),
            "algorithm": "AES-256-GCM",
        }

    except Exception as e:
        return {
            "configured": False,
            "error": f"Invalid base64 encoding: {str(e)}",
            "instructions": "Generate a new key",
        }


def sanitize_api_keys(keys: dict) -> dict:
    """
    Sanitize API keys for logging (show only first/last chars).

    Args:
        keys: Dictionary of API keys

    Returns:
        Sanitized dictionary safe for logging

    Example:
        {"openai": "sk-abc123xyz"} -> {"openai": "sk-...xyz"}
    """
    sanitized = {}
    for provider, key in keys.items():
        if len(key) <= 6:
            sanitized[provider] = "***"
        else:
            sanitized[provider] = f"{key[:3]}...{key[-3:]}"
    return sanitized
