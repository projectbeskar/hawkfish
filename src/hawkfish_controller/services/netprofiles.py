from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any

import aiosqlite

from ..config import settings


@dataclass
class NetworkProfile:
    id: str
    name: str
    libvirt_network: str | None
    bridge: str | None
    vlan: int | None
    mac_policy: str  # "auto" | "fixed"
    count_per_system: int
    cloud_init_network: dict[str, Any] | None
    created_at: str
    labels: dict[str, Any]


async def init_netprofiles() -> None:
    """Initialize network profiles database table."""
    async with aiosqlite.connect(f"{settings.state_dir}/netprofiles.db") as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS hf_netprofiles (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                libvirt_network TEXT,
                bridge TEXT,
                vlan INTEGER,
                mac_policy TEXT NOT NULL,
                count_per_system INTEGER NOT NULL,
                cloud_init_network TEXT,
                created_at TEXT NOT NULL,
                labels TEXT NOT NULL
            )
            """
        )
        await db.commit()


async def create_netprofile(
    name: str,
    libvirt_network: str | None = None,
    bridge: str | None = None,
    vlan: int | None = None,
    mac_policy: str = "auto",
    count_per_system: int = 1,
    cloud_init_network: dict[str, Any] | None = None,
    labels: dict[str, Any] | None = None,
) -> NetworkProfile:
    """Create a new network profile."""
    await init_netprofiles()
    profile_id = uuid.uuid4().hex
    now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # Validate that either libvirt_network or bridge is specified
    if not libvirt_network and not bridge:
        raise ValueError("Either libvirt_network or bridge must be specified")
    
    profile = NetworkProfile(
        id=profile_id,
        name=name,
        libvirt_network=libvirt_network,
        bridge=bridge,
        vlan=vlan,
        mac_policy=mac_policy,
        count_per_system=count_per_system,
        cloud_init_network=cloud_init_network,
        created_at=now,
        labels=labels or {},
    )
    
    async with aiosqlite.connect(f"{settings.state_dir}/netprofiles.db") as db:
        await db.execute(
            "INSERT INTO hf_netprofiles (id, name, libvirt_network, bridge, vlan, mac_policy, count_per_system, cloud_init_network, created_at, labels) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                profile.id,
                profile.name,
                profile.libvirt_network,
                profile.bridge,
                profile.vlan,
                profile.mac_policy,
                profile.count_per_system,
                json.dumps(profile.cloud_init_network) if profile.cloud_init_network else None,
                profile.created_at,
                json.dumps(profile.labels),
            ),
        )
        await db.commit()
    
    return profile


async def list_netprofiles() -> list[NetworkProfile]:
    """List all network profiles."""
    await init_netprofiles()
    async with aiosqlite.connect(f"{settings.state_dir}/netprofiles.db") as db:
        cur = await db.execute(
            "SELECT id, name, libvirt_network, bridge, vlan, mac_policy, count_per_system, cloud_init_network, created_at, labels FROM hf_netprofiles ORDER BY created_at DESC"
        )
        rows = await cur.fetchall()
        await cur.close()
    
    return [
        NetworkProfile(
            id=r[0],
            name=r[1],
            libvirt_network=r[2],
            bridge=r[3],
            vlan=r[4],
            mac_policy=r[5],
            count_per_system=r[6],
            cloud_init_network=json.loads(r[7]) if r[7] else None,
            created_at=r[8],
            labels=json.loads(r[9] or "{}"),
        )
        for r in rows
    ]


async def get_netprofile(profile_id: str) -> NetworkProfile | None:
    """Get a specific network profile by ID."""
    await init_netprofiles()
    async with aiosqlite.connect(f"{settings.state_dir}/netprofiles.db") as db:
        cur = await db.execute(
            "SELECT id, name, libvirt_network, bridge, vlan, mac_policy, count_per_system, cloud_init_network, created_at, labels FROM hf_netprofiles WHERE id=?",
            (profile_id,),
        )
        row = await cur.fetchone()
        await cur.close()
    
    if not row:
        return None
    
    return NetworkProfile(
        id=row[0],
        name=row[1],
        libvirt_network=row[2],
        bridge=row[3],
        vlan=row[4],
        mac_policy=row[5],
        count_per_system=row[6],
        cloud_init_network=json.loads(row[7]) if row[7] else None,
        created_at=row[8],
        labels=json.loads(row[9] or "{}"),
    )


async def get_netprofile_by_name(name: str) -> NetworkProfile | None:
    """Get a network profile by name."""
    await init_netprofiles()
    async with aiosqlite.connect(f"{settings.state_dir}/netprofiles.db") as db:
        cur = await db.execute(
            "SELECT id, name, libvirt_network, bridge, vlan, mac_policy, count_per_system, cloud_init_network, created_at, labels FROM hf_netprofiles WHERE name=?",
            (name,),
        )
        row = await cur.fetchone()
        await cur.close()
    
    if not row:
        return None
    
    return NetworkProfile(
        id=row[0],
        name=row[1],
        libvirt_network=row[2],
        bridge=row[3],
        vlan=row[4],
        mac_policy=row[5],
        count_per_system=row[6],
        cloud_init_network=json.loads(row[7]) if row[7] else None,
        created_at=row[8],
        labels=json.loads(row[9] or "{}"),
    )


async def delete_netprofile(profile_id: str) -> None:
    """Remove a network profile."""
    await init_netprofiles()
    async with aiosqlite.connect(f"{settings.state_dir}/netprofiles.db") as db:
        await db.execute("DELETE FROM hf_netprofiles WHERE id=?", (profile_id,))
        await db.commit()


def generate_cloud_init_network_config(profile: NetworkProfile, system_name: str) -> dict[str, Any] | None:
    """Generate cloud-init network configuration for a system using this profile."""
    if not profile.cloud_init_network:
        return None
    
    # Simple template expansion - replace {system_name} in values
    def expand_template(obj: Any) -> Any:
        if isinstance(obj, str):
            return obj.replace("{system_name}", system_name)
        elif isinstance(obj, dict):
            return {k: expand_template(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [expand_template(item) for item in obj]
        else:
            return obj
    
    return expand_template(profile.cloud_init_network)
