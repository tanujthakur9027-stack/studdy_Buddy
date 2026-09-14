"""
services/auth_service.py — Password hashing and JWT token utilities.

Uses bcrypt directly (avoids passlib + bcrypt 4.x/5.x incompatibility on Python 3.12+).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from config import get_settings

settings = get_settings()

# bcrypt work factor — 12 is a good balance of speed vs security
_ROUNDS = 12


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt. Returns a UTF-8 string."""
    password_bytes = password.encode("utf-8")
    # bcrypt has a 72-byte limit — truncate to be safe
    salt = bcrypt.gensalt(rounds=_ROUNDS)
    hashed = bcrypt.hashpw(password_bytes[:72], salt)
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    try:
        plain_bytes = plain.encode("utf-8")
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(plain_bytes[:72], hashed_bytes)
    except Exception:
        return False


def create_access_token(data: dict) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT. Returns payload dict or None on failure."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return payload
    except JWTError:
        return None
