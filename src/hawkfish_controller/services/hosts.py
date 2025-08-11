from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

import aiosqlite

from ..config import settings


@dataclass
class Host:
    id: str
    uri: str
    name: str
    labels: dict[str, Any]
    capacity: dict[str, int]  # {"vcpus": N, "memMiB": M}
    allocated: dict[str, int]  # {"vcpus": N, "memMiB": M}
    state: str  # "active" | "maintenance" | "error"
    created_at: str


@dataclass
class PlacementRequest:
    vcpus: int
    memory_mib: int
    required_labels: dict[str, Any] | None = None


async def init_hosts() -> None:
    """Initialize hosts database table."""
    async with aiosqlite.connect(f"{settings.state_dir}/hosts.db") as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS hf_hosts (
                id TEXT PRIMARY KEY,
                uri TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                labels TEXT NOT NULL,
                capacity TEXT NOT NULL,
                allocated TEXT NOT NULL,
                state TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def add_host(uri: str, name: str, labels: dict[str, Any] | None = None) -> Host:
    """Add a new host to the pool."""
    await init_hosts()
    host_id = uuid.uuid4().hex
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # Try to connect and get capacity
    try:
        from ..drivers.libvirt_driver import LibvirtDriver
        LibvirtDriver(uri)  # Test connection
        # Get basic capacity info (placeholder - would query libvirt nodeinfo)
        capacity = {"vcpus": 8, "memMiB": 16384}  # Default for demo
    except Exception:
        capacity = {"vcpus": 4, "memMiB": 8192}  # Conservative default
    
    host = Host(
        id=host_id,
        uri=uri,
        name=name,
        labels=labels or {},
        capacity=capacity,
        allocated={"vcpus": 0, "memMiB": 0},
        state="active",
        created_at=now,
    )
    
    async with aiosqlite.connect(f"{settings.state_dir}/hosts.db") as db:
        await db.execute(
            "INSERT INTO hf_hosts (id, uri, name, labels, capacity, allocated, state, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                host.id,
                host.uri,
                host.name,
                json.dumps(host.labels),
                json.dumps(host.capacity),
                json.dumps(host.allocated),
                host.state,
                host.created_at,
            ),
        )
        await db.commit()
    
    return host


async def list_hosts() -> list[Host]:
    """List all hosts in the pool."""
    await init_hosts()
    async with aiosqlite.connect(f"{settings.state_dir}/hosts.db") as db:
        cur = await db.execute(
            "SELECT id, uri, name, labels, capacity, allocated, state, created_at FROM hf_hosts ORDER BY created_at"
        )
        rows = await cur.fetchall()
        await cur.close()
    
    return [
        Host(
            id=r[0],
            uri=r[1],
            name=r[2],
            labels=json.loads(r[3]),
            capacity=json.loads(r[4]),
            allocated=json.loads(r[5]),
            state=r[6],
            created_at=r[7],
        )
        for r in rows
    ]


async def get_host(host_id: str) -> Host | None:
    """Get a specific host by ID."""
    await init_hosts()
    async with aiosqlite.connect(f"{settings.state_dir}/hosts.db") as db:
        cur = await db.execute(
            "SELECT id, uri, name, labels, capacity, allocated, state, created_at FROM hf_hosts WHERE id=?",
            (host_id,),
        )
        row = await cur.fetchone()
        await cur.close()
    
    if not row:
        return None
    
    return Host(
        id=row[0],
        uri=row[1],
        name=row[2],
        labels=json.loads(row[3]),
        capacity=json.loads(row[4]),
        allocated=json.loads(row[5]),
        state=row[6],
        created_at=row[7],
    )


async def delete_host(host_id: str) -> None:
    """Remove a host from the pool."""
    await init_hosts()
    async with aiosqlite.connect(f"{settings.state_dir}/hosts.db") as db:
        await db.execute("DELETE FROM hf_hosts WHERE id=?", (host_id,))
        await db.commit()


async def update_host_allocation(host_id: str, vcpus_delta: int, memory_delta: int) -> None:
    """Update the allocated resources for a host."""
    await init_hosts()
    async with aiosqlite.connect(f"{settings.state_dir}/hosts.db") as db:
        # Get current allocation
        cur = await db.execute("SELECT allocated FROM hf_hosts WHERE id=?", (host_id,))
        row = await cur.fetchone()
        await cur.close()
        
        if not row:
            return
        
        allocated = json.loads(row[0])
        allocated["vcpus"] = max(0, allocated["vcpus"] + vcpus_delta)
        allocated["memMiB"] = max(0, allocated["memMiB"] + memory_delta)
        
        await db.execute(
            "UPDATE hf_hosts SET allocated=? WHERE id=?",
            (json.dumps(allocated), host_id),
        )
        await db.commit()


def _host_fits(host: Host, request: PlacementRequest) -> bool:
    """Check if a host can accommodate the placement request."""
    free_vcpus = host.capacity["vcpus"] - host.allocated["vcpus"]
    free_memory = host.capacity["memMiB"] - host.allocated["memMiB"]
    
    if free_vcpus < request.vcpus or free_memory < request.memory_mib:
        return False
    
    # Check label constraints
    if request.required_labels:
        for key, value in request.required_labels.items():
            if host.labels.get(key) != value:
                return False
    
    return True


async def schedule_placement(request: PlacementRequest) -> Host | None:
    """Find the best host for a placement request using simple spread algorithm."""
    hosts = await list_hosts()
    
    # Filter to hosts that can fit the request and are active
    candidates = [h for h in hosts if h.state == "active" and _host_fits(h, request)]
    
    if not candidates:
        return None
    
    # Simple spread: choose host with least allocated vCPUs
    return min(candidates, key=lambda h: h.allocated["vcpus"])


async def get_default_host() -> Host | None:
    """Get the default host (fallback for single-host setups)."""
    hosts = await list_hosts()
    if not hosts:
        # Auto-add localhost if no hosts configured
        return await add_host(settings.libvirt_uri, "localhost", {"auto": True})
    return hosts[0]
