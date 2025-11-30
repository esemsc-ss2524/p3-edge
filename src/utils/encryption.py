"""
Encryption utilities for P3-Edge application.

Provides helper functions for data encryption and hashing.
"""

import hashlib
import secrets
from typing import Optional, Tuple

from cryptography.fernet import Fernet


def generate_encryption_key() -> bytes:
    """
    Generate a new Fernet encryption key.

    Returns:
        Encryption key bytes
    """
    return Fernet.generate_key()


def encrypt_data(data: bytes, key: bytes) -> bytes:
    """
    Encrypt data using Fernet symmetric encryption.

    Args:
        data: Data to encrypt
        key: Encryption key

    Returns:
        Encrypted data
    """
    cipher = Fernet(key)
    return cipher.encrypt(data)


def decrypt_data(encrypted_data: bytes, key: bytes) -> bytes:
    """
    Decrypt data using Fernet symmetric encryption.

    Args:
        encrypted_data: Encrypted data
        key: Decryption key

    Returns:
        Decrypted data
    """
    cipher = Fernet(key)
    return cipher.decrypt(encrypted_data)


def hash_password(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
    """
    Hash a password using PBKDF2-HMAC-SHA256.

    Args:
        password: Password to hash
        salt: Optional salt (generated if not provided)

    Returns:
        Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_bytes(32)

    password_hash = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        iterations=100000
    )

    return password_hash, salt


def verify_password(password: str, password_hash: bytes, salt: bytes) -> bool:
    """
    Verify a password against a hash.

    Args:
        password: Password to verify
        password_hash: Stored password hash
        salt: Salt used for hashing

    Returns:
        True if password matches
    """
    computed_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(computed_hash, password_hash)


def generate_secure_token(num_bytes: int = 32) -> str:
    """
    Generate a cryptographically secure random token.

    Args:
        num_bytes: Number of random bytes

    Returns:
        Hex-encoded token string
    """
    return secrets.token_hex(num_bytes)


def derive_key_from_password(password: str, salt: bytes) -> bytes:
    """
    Derive an encryption key from a password.

    Args:
        password: User password
        salt: Salt for key derivation

    Returns:
        Derived encryption key
    """
    import base64

    # Use PBKDF2 to derive a key
    key_material = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        iterations=100000,
        dklen=32
    )

    # Encode for Fernet (requires base64url encoding)
    return base64.urlsafe_b64encode(key_material)
