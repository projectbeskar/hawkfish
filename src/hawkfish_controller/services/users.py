"""Simple user management for authentication."""

from __future__ import annotations

import argon2
import aiosqlite

from ..config import settings

# Simple in-memory user store for dev mode
_users: dict[str, dict[str, str]] = {}
ph = argon2.PasswordHasher()


async def init_users() -> None:
    """Initialize user storage."""
    # For now, just use in-memory storage
    # In production, this would use SQLite
    pass


async def user_count() -> int:
    """Get the number of users."""
    await init_users()
    return len(_users)


async def set_user(username: str, password: str, role: str) -> None:
    """Set/create a user with password and role."""
    await init_users()
    password_hash = ph.hash(password)
    _users[username] = {
        "password_hash": password_hash,
        "role": role
    }


async def verify_user(username: str, password: str) -> str | None:
    """Verify user credentials and return role, or None if invalid."""
    await init_users()
    
    if username not in _users:
        return None
    
    user_data = _users[username]
    try:
        ph.verify(user_data["password_hash"], password)
        return user_data["role"]
    except argon2.exceptions.VerifyMismatchError:
        return None


async def delete_user(username: str) -> bool:
    """Delete a user. Returns True if user existed."""
    await init_users()
    return _users.pop(username, None) is not None


async def list_users() -> list[dict[str, str]]:
    """List all users (without password hashes)."""
    await init_users()
    return [
        {"username": username, "role": data["role"]}
        for username, data in _users.items()
    ]
