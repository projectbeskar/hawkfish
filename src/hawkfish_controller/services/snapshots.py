from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

import aiosqlite

from ..config import settings


@dataclass
class Snapshot:
    id: str
    system_id: str
    name: str
    description: str | None
    created_at: str
    size_bytes: int | None
    state: str  # "Creating", "Ready", "Reverting", "Failed"
    libvirt_snapshot_name: str | None
    metadata: dict[str, Any]


async def init_snapshots() -> None:
    """Initialize snapshots database table."""
    async with aiosqlite.connect(f"{settings.state_dir}/snapshots.db") as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS hf_snapshots (
                id TEXT PRIMARY KEY,
                system_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                created_at TEXT NOT NULL,
                size_bytes INTEGER,
                state TEXT NOT NULL,
                libvirt_snapshot_name TEXT,
                metadata TEXT NOT NULL,
                UNIQUE(system_id, name)
            )
            """
        )
        await db.commit()


async def create_snapshot(
    system_id: str,
    name: str | None = None,
    description: str | None = None,
) -> Snapshot:
    """Create a new snapshot record (actual snapshot creation happens in background task)."""
    await init_snapshots()
    
    snapshot_id = uuid.uuid4().hex
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # Generate name if not provided
    if not name:
        timestamp = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        name = f"snapshot-{timestamp}-{snapshot_id[:8]}"
    
    # Libvirt snapshot name (deterministic)
    libvirt_name = f"hf-{snapshot_id[:12]}"
    
    snapshot = Snapshot(
        id=snapshot_id,
        system_id=system_id,
        name=name,
        description=description,
        created_at=now,
        size_bytes=None,
        state="Creating",
        libvirt_snapshot_name=libvirt_name,
        metadata={},
    )
    
    async with aiosqlite.connect(f"{settings.state_dir}/snapshots.db") as db:
        await db.execute(
            "INSERT INTO hf_snapshots (id, system_id, name, description, created_at, size_bytes, state, libvirt_snapshot_name, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                snapshot.id,
                snapshot.system_id,
                snapshot.name,
                snapshot.description,
                snapshot.created_at,
                snapshot.size_bytes,
                snapshot.state,
                snapshot.libvirt_snapshot_name,
                json.dumps(snapshot.metadata),
            ),
        )
        await db.commit()
    
    return snapshot


async def list_snapshots(system_id: str) -> list[Snapshot]:
    """List all snapshots for a system."""
    await init_snapshots()
    async with aiosqlite.connect(f"{settings.state_dir}/snapshots.db") as db:
        cur = await db.execute(
            "SELECT id, system_id, name, description, created_at, size_bytes, state, libvirt_snapshot_name, metadata FROM hf_snapshots WHERE system_id=? ORDER BY created_at DESC",
            (system_id,),
        )
        rows = await cur.fetchall()
        await cur.close()
    
    return [
        Snapshot(
            id=r[0],
            system_id=r[1],
            name=r[2],
            description=r[3],
            created_at=r[4],
            size_bytes=r[5],
            state=r[6],
            libvirt_snapshot_name=r[7],
            metadata=json.loads(r[8] or "{}"),
        )
        for r in rows
    ]


async def get_snapshot(system_id: str, snapshot_id: str) -> Snapshot | None:
    """Get a specific snapshot."""
    await init_snapshots()
    async with aiosqlite.connect(f"{settings.state_dir}/snapshots.db") as db:
        cur = await db.execute(
            "SELECT id, system_id, name, description, created_at, size_bytes, state, libvirt_snapshot_name, metadata FROM hf_snapshots WHERE system_id=? AND id=?",
            (system_id, snapshot_id),
        )
        row = await cur.fetchone()
        await cur.close()
    
    if not row:
        return None
    
    return Snapshot(
        id=row[0],
        system_id=row[1],
        name=row[2],
        description=row[3],
        created_at=row[4],
        size_bytes=row[5],
        state=row[6],
        libvirt_snapshot_name=row[7],
        metadata=json.loads(row[8] or "{}"),
    )


async def update_snapshot_state(snapshot_id: str, state: str, size_bytes: int | None = None, metadata: dict[str, Any] | None = None) -> None:
    """Update snapshot state and metadata."""
    await init_snapshots()
    
    # Build safe SQL with known column names
    if size_bytes is not None and metadata is not None:
        sql = "UPDATE hf_snapshots SET state = ?, size_bytes = ?, metadata = ? WHERE id = ?"
        params = [state, size_bytes, json.dumps(metadata), snapshot_id]
    elif size_bytes is not None:
        sql = "UPDATE hf_snapshots SET state = ?, size_bytes = ? WHERE id = ?"
        params = [state, size_bytes, snapshot_id]
    elif metadata is not None:
        sql = "UPDATE hf_snapshots SET state = ?, metadata = ? WHERE id = ?"
        params = [state, json.dumps(metadata), snapshot_id]
    else:
        sql = "UPDATE hf_snapshots SET state = ? WHERE id = ?"
        params = [state, snapshot_id]
    
    async with aiosqlite.connect(f"{settings.state_dir}/snapshots.db") as db:
        await db.execute(sql, params)
        await db.commit()


async def delete_snapshot(snapshot_id: str) -> None:
    """Remove a snapshot record."""
    await init_snapshots()
    async with aiosqlite.connect(f"{settings.state_dir}/snapshots.db") as db:
        await db.execute("DELETE FROM hf_snapshots WHERE id=?", (snapshot_id,))
        await db.commit()


async def cleanup_old_snapshots(system_id: str, max_snapshots: int = 10) -> list[str]:
    """Clean up old snapshots if limit exceeded, returning list of deleted snapshot IDs."""
    snapshots = await list_snapshots(system_id)
    if len(snapshots) <= max_snapshots:
        return []
    
    # Delete oldest snapshots beyond limit
    to_delete = snapshots[max_snapshots:]
    deleted_ids = []
    
    for snapshot in to_delete:
        await delete_snapshot(snapshot.id)
        deleted_ids.append(snapshot.id)
    
    return deleted_ids
