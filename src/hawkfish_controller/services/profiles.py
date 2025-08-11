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
    project_id: str = "default"


async def init_profiles() -> None:
    os.makedirs(settings.state_dir, exist_ok=True)
    async with aiosqlite.connect(f"{settings.state_dir}/profiles.db") as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS hf_profiles (
                id TEXT PRIMARY KEY,
                spec TEXT NOT NULL,
                created_at TEXT NOT NULL,
                project_id TEXT DEFAULT 'default'
            )
            """
        )
        
        # Add project_id column if it doesn't exist (migration)
        try:
            await db.execute("ALTER TABLE hf_profiles ADD COLUMN project_id TEXT DEFAULT 'default'")
        except Exception:
            pass  # Column already exists
        await db.commit()


async def list_profiles(project_id: str | None = None) -> list[Profile]:
    await init_profiles()
    async with aiosqlite.connect(f"{settings.state_dir}/profiles.db") as db:
        if project_id:
            cur = await db.execute("SELECT id, spec, created_at, project_id FROM hf_profiles WHERE project_id = ? ORDER BY created_at DESC", (project_id,))
        else:
            cur = await db.execute("SELECT id, spec, created_at, project_id FROM hf_profiles ORDER BY created_at DESC")
        rows = await cur.fetchall()
        await cur.close()
    return [Profile(id=r[0], spec=json.loads(r[1]), created_at=r[2], project_id=r[3] if len(r) > 3 else "default") for r in rows]


async def get_profile(profile_id: str) -> Profile | None:
    await init_profiles()
    async with aiosqlite.connect(f"{settings.state_dir}/profiles.db") as db:
        cur = await db.execute("SELECT id, spec, created_at, project_id FROM hf_profiles WHERE id=?", (profile_id,))
        row = await cur.fetchone()
        await cur.close()
    if not row:
        return None
    return Profile(id=row[0], spec=json.loads(row[1]), created_at=row[2], project_id=row[3] if len(row) > 3 else "default")


async def delete_profile(profile_id: str) -> None:
    await init_profiles()
    async with aiosqlite.connect(f"{settings.state_dir}/profiles.db") as db:
        await db.execute("DELETE FROM hf_profiles WHERE id=?", (profile_id,))
        await db.commit()


async def create_profile(profile_id: str, spec: dict[str, Any], project_id: str = "default") -> Profile:
    await init_profiles()
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    async with aiosqlite.connect(f"{settings.state_dir}/profiles.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO hf_profiles (id, spec, created_at, project_id) VALUES (?, ?, ?, ?)",
            (profile_id, json.dumps(spec), now, project_id),
        )
        await db.commit()
    return Profile(id=profile_id, spec=spec, created_at=now, project_id=project_id)


