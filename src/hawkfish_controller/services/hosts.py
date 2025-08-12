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


async def set_host_maintenance(host_id: str, maintenance: bool) -> bool:
    """Set host maintenance mode."""
    await _init_hosts()
    
    new_state = "maintenance" if maintenance else "active"
    
    async with aiosqlite.connect(f"{settings.state_dir}/hawkfish.db") as db:
        cursor = await db.execute(
            "UPDATE hf_hosts SET state = ? WHERE id = ?",
            (new_state, host_id)
        )
        updated = cursor.rowcount > 0
        await db.commit()
        
        return updated


async def get_systems_on_host(host_id: str) -> list[dict[str, Any]]:
    """Get list of systems currently running on a host."""
    # This would typically query the Systems table filtered by host_id
    # For now, return empty list as systems don't track host placement yet
    await _init_hosts()
    
    # In a full implementation, this would query:
    # SELECT system_id, name, state FROM hf_systems WHERE host_id = ?
    # For now, return mock data for testing
    return []


async def migrate_system(system_id: str, source_host_id: str, target_host_id: str, live: bool = True) -> str:
    """Initiate system migration between hosts. Returns task ID."""
    from .tasks import task_service
    
    task = await task_service.create(name=f"Migrate {system_id} from {source_host_id} to {target_host_id}")
    
    async def migration_job(task_id: str) -> None:
        try:
            await task_service.update(task_id, state="Running", percent=1, message="Starting migration")
            
            # Get host details
            source_host = await get_host(source_host_id)
            target_host = await get_host(target_host_id)
            
            if not source_host or not target_host:
                raise RuntimeError("Source or target host not found")
            
            if target_host.state == "maintenance":
                raise RuntimeError("Target host is in maintenance mode")
            
            await task_service.update(task_id, percent=10, message="Validating migration compatibility")
            
            # In a real implementation, this would:
            # 1. Check CPU compatibility between hosts
            # 2. Ensure shared storage or copy disks
            # 3. Perform pre-migration checks
            # 4. Execute libvirt migrate/migrateToURI3
            # 5. Update system host assignment
            
            await task_service.update(task_id, percent=30, message="Checking CPU compatibility")
            # Mock CPU check delay
            import asyncio
            await asyncio.sleep(1)
            
            await task_service.update(task_id, percent=50, message="Starting live migration")
            # Mock migration process
            await asyncio.sleep(2)
            
            await task_service.update(task_id, percent=80, message="Finalizing migration")
            await asyncio.sleep(1)
            
            # Update host allocations (in real implementation)
            # This would move resource allocation from source to target
            
            await task_service.update(task_id, percent=100, state="Completed", message="Migration completed successfully", end=True)
            
            # Emit migration events
            from .events import publish_event
            from .events import subscription_store
            await publish_event("SystemMigrated", {
                "systemId": system_id,
                "sourceHostId": source_host_id,
                "targetHostId": target_host_id,
                "migrationType": "live" if live else "offline"
            }, subscription_store)
            
        except Exception as e:
            await task_service.update(task_id, state="Exception", message=str(e), end=True)
            raise
    
    # Run migration in background
    await task_service.run_background(
        name=f"Migrate {system_id}",
        coro_factory=lambda tid: migration_job(tid)
    )
    
    return task.id


async def evacuate_host(host_id: str) -> list[str]:
    """Evacuate all systems from a host via live migration. Returns list of task IDs."""
    await _init_hosts()
    
    # Get systems on this host
    systems = await get_systems_on_host(host_id)
    
    if not systems:
        return []
    
    # Find target hosts for migration
    hosts = await list_hosts()
    available_hosts = [h for h in hosts if h.id != host_id and h.state == "active"]
    
    if not available_hosts:
        raise RuntimeError("No available hosts for evacuation")
    
    task_ids = []
    
    for system in systems:
        # Simple round-robin assignment
        target_host = available_hosts[len(task_ids) % len(available_hosts)]
        
        task_id = await migrate_system(
            system_id=system["system_id"],
            source_host_id=host_id,
            target_host_id=target_host.id,
            live=True
        )
        task_ids.append(task_id)
    
    return task_ids
