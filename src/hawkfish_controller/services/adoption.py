from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

import aiosqlite

from ..config import settings


@dataclass
class Adoption:
    id: str
    host_id: str
    libvirt_uuid: str
    system_id: str
    adopted_at: str
    tags: dict[str, Any]


async def init_adoptions() -> None:
    """Initialize adoptions database table."""
    async with aiosqlite.connect(f"{settings.state_dir}/adoptions.db") as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS hf_adoptions (
                id TEXT PRIMARY KEY,
                host_id TEXT NOT NULL,
                libvirt_uuid TEXT NOT NULL,
                system_id TEXT NOT NULL,
                adopted_at TEXT NOT NULL,
                tags TEXT NOT NULL,
                UNIQUE(host_id, libvirt_uuid)
            )
            """
        )
        await db.commit()


async def create_adoption(
    host_id: str,
    libvirt_uuid: str,
    system_id: str,
    tags: dict[str, Any] | None = None,
) -> Adoption:
    """Create a new adoption mapping."""
    await init_adoptions()
    adoption_id = uuid.uuid4().hex
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    adoption = Adoption(
        id=adoption_id,
        host_id=host_id,
        libvirt_uuid=libvirt_uuid,
        system_id=system_id,
        adopted_at=now,
        tags=tags or {},
    )
    
    async with aiosqlite.connect(f"{settings.state_dir}/adoptions.db") as db:
        await db.execute(
            "INSERT OR REPLACE INTO hf_adoptions (id, host_id, libvirt_uuid, system_id, adopted_at, tags) VALUES (?, ?, ?, ?, ?, ?)",
            (
                adoption.id,
                adoption.host_id,
                adoption.libvirt_uuid,
                adoption.system_id,
                adoption.adopted_at,
                json.dumps(adoption.tags),
            ),
        )
        await db.commit()
    
    return adoption


async def list_adoptions() -> list[Adoption]:
    """List all adoption mappings."""
    await init_adoptions()
    async with aiosqlite.connect(f"{settings.state_dir}/adoptions.db") as db:
        cur = await db.execute(
            "SELECT id, host_id, libvirt_uuid, system_id, adopted_at, tags FROM hf_adoptions ORDER BY adopted_at DESC"
        )
        rows = await cur.fetchall()
        await cur.close()
    
    return [
        Adoption(
            id=r[0],
            host_id=r[1],
            libvirt_uuid=r[2],
            system_id=r[3],
            adopted_at=r[4],
            tags=json.loads(r[5] or "{}"),
        )
        for r in rows
    ]


async def get_adoption_by_system_id(system_id: str) -> Adoption | None:
    """Get adoption mapping by system ID."""
    await init_adoptions()
    async with aiosqlite.connect(f"{settings.state_dir}/adoptions.db") as db:
        cur = await db.execute(
            "SELECT id, host_id, libvirt_uuid, system_id, adopted_at, tags FROM hf_adoptions WHERE system_id=?",
            (system_id,),
        )
        row = await cur.fetchone()
        await cur.close()
    
    if not row:
        return None
    
    return Adoption(
        id=row[0],
        host_id=row[1],
        libvirt_uuid=row[2],
        system_id=row[3],
        adopted_at=row[4],
        tags=json.loads(row[5] or "{}"),
    )


async def get_adoption_by_host_and_uuid(host_id: str, libvirt_uuid: str) -> Adoption | None:
    """Get adoption mapping by host and libvirt UUID."""
    await init_adoptions()
    async with aiosqlite.connect(f"{settings.state_dir}/adoptions.db") as db:
        cur = await db.execute(
            "SELECT id, host_id, libvirt_uuid, system_id, adopted_at, tags FROM hf_adoptions WHERE host_id=? AND libvirt_uuid=?",
            (host_id, libvirt_uuid),
        )
        row = await cur.fetchone()
        await cur.close()
    
    if not row:
        return None
    
    return Adoption(
        id=row[0],
        host_id=row[1],
        libvirt_uuid=row[2],
        system_id=row[3],
        adopted_at=row[4],
        tags=json.loads(row[5] or "{}"),
    )


async def delete_adoption(system_id: str) -> None:
    """Remove an adoption mapping."""
    await init_adoptions()
    async with aiosqlite.connect(f"{settings.state_dir}/adoptions.db") as db:
        await db.execute("DELETE FROM hf_adoptions WHERE system_id=?", (system_id,))
        await db.commit()


async def update_adoption_tags(system_id: str, tags: dict[str, Any]) -> None:
    """Update tags for an adoption mapping."""
    await init_adoptions()
    async with aiosqlite.connect(f"{settings.state_dir}/adoptions.db") as db:
        await db.execute(
            "UPDATE hf_adoptions SET tags=? WHERE system_id=?",
            (json.dumps(tags), system_id),
        )
        await db.commit()
