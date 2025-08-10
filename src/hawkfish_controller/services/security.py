from __future__ import annotations

import os
import time
from pathlib import Path

import aiosqlite
from argon2 import PasswordHasher

from ..config import settings

ph = PasswordHasher()


async def ensure_user_tables(db_path: str) -> None:
    Path(os.path.dirname(db_path)).mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS hf_users (
                username TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def set_user(username: str, password: str, role: str) -> None:
    await ensure_user_tables(f"{settings.state_dir}/auth.db")
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    pwd_hash = ph.hash(password)
    async with aiosqlite.connect(f"{settings.state_dir}/auth.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO hf_users (username, password_hash, role, updated_at) VALUES (?, ?, ?, ?)",
            (username, pwd_hash, role, now),
        )
        await db.commit()


async def verify_user(username: str, password: str) -> str | None:
    await ensure_user_tables(f"{settings.state_dir}/auth.db")
    async with aiosqlite.connect(f"{settings.state_dir}/auth.db") as db:
        cur = await db.execute("SELECT password_hash, role FROM hf_users WHERE username=?", (username,))
        row = await cur.fetchone()
        await cur.close()
    if not row:
        return None
    pwd_hash, role = str(row[0]), str(row[1])
    try:
        ph.verify(pwd_hash, password)
        return role
    except Exception:
        return None


def require_role(required: str, actual: str) -> bool:
    order = {"viewer": 1, "operator": 2, "admin": 3}
    return order.get(actual, 0) >= order.get(required, 0)


