from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiosqlite

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class StoragePool:
    """A libvirt storage pool."""
    id: str
    name: str
    type: str  # "dir", "nfs", "lvm", "iscsi"
    target_path: str
    capacity_bytes: int
    allocated_bytes: int
    available_bytes: int
    state: str  # "active", "inactive", "error"
    autostart: bool
    host_id: str
    created_at: str
    config: dict[str, Any]  # Pool-specific configuration


@dataclass
class StorageVolume:
    """A storage volume in a pool."""
    id: str
    name: str
    pool_id: str
    capacity_bytes: int
    allocated_bytes: int
    format: str  # "qcow2", "raw", "vmdk"
    target_path: str
    state: str  # "active", "inactive"
    attached_to: str | None  # System ID if attached
    project_id: str
    created_at: str
    labels: dict[str, Any]


class StorageService:
    """Service for managing storage pools and volumes."""
    
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or f"{settings.state_dir}/hawkfish.db"
        self._initialized = False
    
    async def init(self) -> None:
        """Initialize storage tables."""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            # Storage pools table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS hf_storage_pools (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    target_path TEXT NOT NULL,
                    capacity_bytes INTEGER NOT NULL DEFAULT 0,
                    allocated_bytes INTEGER NOT NULL DEFAULT 0,
                    available_bytes INTEGER NOT NULL DEFAULT 0,
                    state TEXT NOT NULL DEFAULT 'inactive',
                    autostart BOOLEAN DEFAULT FALSE,
                    host_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    config TEXT
                )
            """)
            
            # Storage volumes table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS hf_storage_volumes (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    pool_id TEXT NOT NULL,
                    capacity_bytes INTEGER NOT NULL,
                    allocated_bytes INTEGER NOT NULL DEFAULT 0,
                    format TEXT NOT NULL DEFAULT 'qcow2',
                    target_path TEXT NOT NULL,
                    state TEXT NOT NULL DEFAULT 'inactive',
                    attached_to TEXT,
                    project_id TEXT DEFAULT 'default',
                    created_at TEXT NOT NULL,
                    labels TEXT,
                    FOREIGN KEY (pool_id) REFERENCES hf_storage_pools (id) ON DELETE CASCADE
                )
            """)
            
            # Volume attachments table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS hf_volume_attachments (
                    id TEXT PRIMARY KEY,
                    volume_id TEXT NOT NULL,
                    system_id TEXT NOT NULL,
                    device TEXT NOT NULL,
                    attached_at TEXT NOT NULL,
                    FOREIGN KEY (volume_id) REFERENCES hf_storage_volumes (id) ON DELETE CASCADE
                )
            """)
            
            await db.commit()
        
        self._initialized = True
        logger.info("Storage service initialized")
    
    async def create_pool(
        self,
        name: str,
        pool_type: str,
        target_path: str,
        host_id: str,
        config: dict[str, Any] | None = None,
        autostart: bool = True
    ) -> StoragePool:
        """Create a new storage pool."""
        await self.init()
        
        pool_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        config = config or {}
        
        # In a real implementation, this would call libvirt to define the pool
        # For now, simulate pool creation
        capacity_bytes = config.get("capacity_gb", 100) * 1024 * 1024 * 1024  # Default 100GB
        
        pool = StoragePool(
            id=pool_id,
            name=name,
            type=pool_type,
            target_path=target_path,
            capacity_bytes=capacity_bytes,
            allocated_bytes=0,
            available_bytes=capacity_bytes,
            state="active" if autostart else "inactive",
            autostart=autostart,
            host_id=host_id,
            created_at=created_at,
            config=config
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO hf_storage_pools 
                (id, name, type, target_path, capacity_bytes, allocated_bytes, 
                 available_bytes, state, autostart, host_id, created_at, config)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pool_id, name, pool_type, target_path, capacity_bytes, 0,
                capacity_bytes, pool.state, autostart, host_id, created_at,
                json.dumps(config)
            ))
            await db.commit()
        
        logger.info(f"Created storage pool: {name} ({pool_type}) on host {host_id}")
        return pool
    
    async def list_pools(self, host_id: str | None = None) -> list[StoragePool]:
        """List storage pools."""
        await self.init()
        
        query = """
            SELECT id, name, type, target_path, capacity_bytes, allocated_bytes,
                   available_bytes, state, autostart, host_id, created_at, config
            FROM hf_storage_pools
        """
        params = []
        
        if host_id:
            query += " WHERE host_id = ?"
            params.append(host_id)
        
        query += " ORDER BY name"
        
        pools = []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    pools.append(StoragePool(
                        id=row[0],
                        name=row[1],
                        type=row[2],
                        target_path=row[3],
                        capacity_bytes=row[4],
                        allocated_bytes=row[5],
                        available_bytes=row[6],
                        state=row[7],
                        autostart=bool(row[8]),
                        host_id=row[9],
                        created_at=row[10],
                        config=json.loads(row[11]) if row[11] else {}
                    ))
        
        return pools
    
    async def get_pool(self, pool_id: str) -> StoragePool | None:
        """Get storage pool by ID."""
        await self.init()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, name, type, target_path, capacity_bytes, allocated_bytes,
                       available_bytes, state, autostart, host_id, created_at, config
                FROM hf_storage_pools WHERE id = ?
            """, (pool_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                
                return StoragePool(
                    id=row[0],
                    name=row[1],
                    type=row[2],
                    target_path=row[3],
                    capacity_bytes=row[4],
                    allocated_bytes=row[5],
                    available_bytes=row[6],
                    state=row[7],
                    autostart=bool(row[8]),
                    host_id=row[9],
                    created_at=row[10],
                    config=json.loads(row[11]) if row[11] else {}
                )
    
    async def delete_pool(self, pool_id: str) -> bool:
        """Delete a storage pool."""
        await self.init()
        
        # Check if pool has volumes
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT COUNT(*) FROM hf_storage_volumes WHERE pool_id = ?
            """, (pool_id,)) as cursor:
                count = (await cursor.fetchone())[0]
                if count > 0:
                    raise ValueError(f"Pool has {count} volumes. Remove them first.")
            
            # Delete pool
            cursor = await db.execute("DELETE FROM hf_storage_pools WHERE id = ?", (pool_id,))
            deleted = cursor.rowcount > 0
            await db.commit()
            
            return deleted
    
    async def create_volume(
        self,
        name: str,
        pool_id: str,
        capacity_bytes: int,
        format: str = "qcow2",
        project_id: str = "default",
        labels: dict[str, Any] | None = None
    ) -> StorageVolume:
        """Create a new storage volume."""
        await self.init()
        
        # Check pool exists and has capacity
        pool = await self.get_pool(pool_id)
        if not pool:
            raise ValueError(f"Pool {pool_id} not found")
        
        if pool.available_bytes < capacity_bytes:
            raise ValueError(f"Insufficient pool capacity: {pool.available_bytes} < {capacity_bytes}")
        
        volume_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        labels = labels or {}
        
        # Generate target path
        target_path = f"{pool.target_path}/{name}.{format}"
        
        volume = StorageVolume(
            id=volume_id,
            name=name,
            pool_id=pool_id,
            capacity_bytes=capacity_bytes,
            allocated_bytes=0,  # Thin provisioned initially
            format=format,
            target_path=target_path,
            state="inactive",
            attached_to=None,
            project_id=project_id,
            created_at=created_at,
            labels=labels
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            # Create volume record
            await db.execute("""
                INSERT INTO hf_storage_volumes 
                (id, name, pool_id, capacity_bytes, allocated_bytes, format,
                 target_path, state, attached_to, project_id, created_at, labels)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                volume_id, name, pool_id, capacity_bytes, 0, format,
                target_path, "inactive", None, project_id, created_at,
                json.dumps(labels)
            ))
            
            # Update pool allocated space
            await db.execute("""
                UPDATE hf_storage_pools 
                SET allocated_bytes = allocated_bytes + ?,
                    available_bytes = available_bytes - ?
                WHERE id = ?
            """, (capacity_bytes, capacity_bytes, pool_id))
            
            await db.commit()
        
        logger.info(f"Created storage volume: {name} ({capacity_bytes} bytes) in pool {pool_id}")
        return volume
    
    async def list_volumes(
        self,
        pool_id: str | None = None,
        project_id: str | None = None
    ) -> list[StorageVolume]:
        """List storage volumes."""
        await self.init()
        
        query = """
            SELECT id, name, pool_id, capacity_bytes, allocated_bytes, format,
                   target_path, state, attached_to, project_id, created_at, labels
            FROM hf_storage_volumes
            WHERE 1=1
        """
        params = []
        
        if pool_id:
            query += " AND pool_id = ?"
            params.append(pool_id)
        
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        
        query += " ORDER BY name"
        
        volumes = []
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    volumes.append(StorageVolume(
                        id=row[0],
                        name=row[1],
                        pool_id=row[2],
                        capacity_bytes=row[3],
                        allocated_bytes=row[4],
                        format=row[5],
                        target_path=row[6],
                        state=row[7],
                        attached_to=row[8],
                        project_id=row[9],
                        created_at=row[10],
                        labels=json.loads(row[11]) if row[11] else {}
                    ))
        
        return volumes
    
    async def get_volume(self, volume_id: str) -> StorageVolume | None:
        """Get storage volume by ID."""
        await self.init()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, name, pool_id, capacity_bytes, allocated_bytes, format,
                       target_path, state, attached_to, project_id, created_at, labels
                FROM hf_storage_volumes WHERE id = ?
            """, (volume_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                
                return StorageVolume(
                    id=row[0],
                    name=row[1],
                    pool_id=row[2],
                    capacity_bytes=row[3],
                    allocated_bytes=row[4],
                    format=row[5],
                    target_path=row[6],
                    state=row[7],
                    attached_to=row[8],
                    project_id=row[9],
                    created_at=row[10],
                    labels=json.loads(row[11]) if row[11] else {}
                )
    
    async def delete_volume(self, volume_id: str) -> bool:
        """Delete a storage volume."""
        await self.init()
        
        volume = await self.get_volume(volume_id)
        if not volume:
            return False
        
        if volume.attached_to:
            raise ValueError(f"Volume is attached to system {volume.attached_to}. Detach first.")
        
        async with aiosqlite.connect(self.db_path) as db:
            # Delete volume
            cursor = await db.execute("DELETE FROM hf_storage_volumes WHERE id = ?", (volume_id,))
            deleted = cursor.rowcount > 0
            
            if deleted:
                # Update pool allocated space
                await db.execute("""
                    UPDATE hf_storage_pools 
                    SET allocated_bytes = allocated_bytes - ?,
                        available_bytes = available_bytes + ?
                    WHERE id = ?
                """, (volume.capacity_bytes, volume.capacity_bytes, volume.pool_id))
            
            await db.commit()
            
            return deleted
    
    async def attach_volume(self, volume_id: str, system_id: str, device: str) -> bool:
        """Attach a volume to a system."""
        await self.init()
        
        volume = await self.get_volume(volume_id)
        if not volume:
            raise ValueError(f"Volume {volume_id} not found")
        
        if volume.attached_to:
            raise ValueError(f"Volume is already attached to system {volume.attached_to}")
        
        attachment_id = str(uuid.uuid4())
        attached_at = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Create attachment record
            await db.execute("""
                INSERT INTO hf_volume_attachments (id, volume_id, system_id, device, attached_at)
                VALUES (?, ?, ?, ?, ?)
            """, (attachment_id, volume_id, system_id, device, attached_at))
            
            # Update volume state
            await db.execute("""
                UPDATE hf_storage_volumes 
                SET attached_to = ?, state = 'active'
                WHERE id = ?
            """, (system_id, volume_id))
            
            await db.commit()
        
        logger.info(f"Attached volume {volume_id} to system {system_id} as {device}")
        return True
    
    async def detach_volume(self, volume_id: str) -> bool:
        """Detach a volume from its system."""
        await self.init()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Remove attachment record
            cursor = await db.execute("""
                DELETE FROM hf_volume_attachments WHERE volume_id = ?
            """, (volume_id,))
            detached = cursor.rowcount > 0
            
            if detached:
                # Update volume state
                await db.execute("""
                    UPDATE hf_storage_volumes 
                    SET attached_to = NULL, state = 'inactive'
                    WHERE id = ?
                """, (volume_id,))
            
            await db.commit()
            
            if detached:
                logger.info(f"Detached volume {volume_id}")
            
            return detached
    
    async def resize_volume(self, volume_id: str, new_capacity_bytes: int) -> bool:
        """Resize a storage volume."""
        await self.init()
        
        volume = await self.get_volume(volume_id)
        if not volume:
            raise ValueError(f"Volume {volume_id} not found")
        
        if new_capacity_bytes <= volume.capacity_bytes:
            raise ValueError("New capacity must be larger than current capacity")
        
        size_increase = new_capacity_bytes - volume.capacity_bytes
        
        # Check pool has available space
        pool = await self.get_pool(volume.pool_id)
        if not pool:
            raise ValueError(f"Pool {volume.pool_id} not found")
        
        if pool.available_bytes < size_increase:
            raise ValueError(f"Insufficient pool capacity for resize: {pool.available_bytes} < {size_increase}")
        
        async with aiosqlite.connect(self.db_path) as db:
            # Update volume capacity
            await db.execute("""
                UPDATE hf_storage_volumes 
                SET capacity_bytes = ?
                WHERE id = ?
            """, (new_capacity_bytes, volume_id))
            
            # Update pool allocation
            await db.execute("""
                UPDATE hf_storage_pools 
                SET allocated_bytes = allocated_bytes + ?,
                    available_bytes = available_bytes - ?
                WHERE id = ?
            """, (size_increase, size_increase, volume.pool_id))
            
            await db.commit()
        
        logger.info(f"Resized volume {volume_id} from {volume.capacity_bytes} to {new_capacity_bytes} bytes")
        return True


# Global storage service instance
storage_service = StorageService()
