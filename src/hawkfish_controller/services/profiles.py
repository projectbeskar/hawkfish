from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any

import aiosqlite

from ..config import settings


@dataclass
class Profile:
    id: str
    spec: dict[str, Any]
    created_at: str


async def init_profiles() -> None:
    os.makedirs(settings.state_dir, exist_ok=True)
    async with aiosqlite.connect(f"{settings.state_dir}/profiles.db") as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS hf_profiles (
                id TEXT PRIMARY KEY,
                spec TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def list_profiles() -> list[Profile]:
    await init_profiles()
    async with aiosqlite.connect(f"{settings.state_dir}/profiles.db") as db:
        cur = await db.execute("SELECT id, spec, created_at FROM hf_profiles ORDER BY created_at DESC")
        rows = await cur.fetchall()
        await cur.close()
    return [Profile(id=r[0], spec=json.loads(r[1]), created_at=r[2]) for r in rows]


async def get_profile(profile_id: str) -> Profile | None:
    await init_profiles()
    async with aiosqlite.connect(f"{settings.state_dir}/profiles.db") as db:
        cur = await db.execute("SELECT id, spec, created_at FROM hf_profiles WHERE id=?", (profile_id,))
        row = await cur.fetchone()
        await cur.close()
    if not row:
        return None
    return Profile(id=row[0], spec=json.loads(row[1]), created_at=row[2])


async def delete_profile(profile_id: str) -> None:
    await init_profiles()
    async with aiosqlite.connect(f"{settings.state_dir}/profiles.db") as db:
        await db.execute("DELETE FROM hf_profiles WHERE id=?", (profile_id,))
        await db.commit()


async def create_profile(profile_id: str, spec: dict[str, Any]) -> Profile:
    await init_profiles()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    async with aiosqlite.connect(f"{settings.state_dir}/profiles.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO hf_profiles (id, spec, created_at) VALUES (?, ?, ?)",
            (profile_id, json.dumps(spec), now),
        )
        await db.commit()
    return Profile(id=profile_id, spec=spec, created_at=now)


