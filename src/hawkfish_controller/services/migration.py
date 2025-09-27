"""
Live migration service for moving systems between hosts.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any

import aiosqlite

from ..config import settings
from ..drivers.libvirt_driver import LibvirtDriver, LibvirtError


class MigrationService:
    """Service for live migration operations."""
    
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or f"{settings.state_dir}/hawkfish.db"
        
        # Migration configuration
        self.default_flags = {
            "live": True,
            "tunneled": True,
            "compressed": False,
            "auto_converge": True,
            "copy_storage": False,
            "bandwidth_mbps": 100,
            "max_downtime_ms": 300
        }
    
    async def init_migration_tables(self) -> None:
        """Initialize migration tracking tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS hf_migrations (
                    id TEXT PRIMARY KEY,
                    system_id TEXT NOT NULL,
                    source_host_id TEXT NOT NULL,
                    target_host_id TEXT NOT NULL,
                    migration_type TEXT NOT NULL,
                    flags TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    downtime_ms INTEGER,
                    error_message TEXT,
                    created_by TEXT
                )
            """)
            await db.commit()
    
    async def pre_migration_checks(
        self, 
        system_id: str, 
        source_host: dict[str, Any], 
        target_host: dict[str, Any]
    ) -> dict[str, Any]:
        """Perform pre-migration compatibility checks."""
        checks = {
            "cpu_compatible": True,
            "shared_storage": False,
            "memory_available": True,
            "network_reachable": True,
            "warnings": [],
            "copy_storage_required": False
        }
        
        # TODO: Real CPU compatibility checking via libvirt capabilities
        # For now, assume compatible
        
        # Check if storage is shared between hosts
        # This is a simplified check - in reality, we'd examine storage pool types
        source_uri = source_host.get("uri", "")
        target_uri = target_host.get("uri", "")
        
        # If both hosts are on same machine (for testing), consider storage shared
        if source_uri == target_uri or ("localhost" in source_uri and "localhost" in target_uri):
            checks["shared_storage"] = True
        else:
            # For different hosts, we'd need to check storage pool backend
            # For now, default to copy-storage migration
            checks["copy_storage_required"] = True
            checks["warnings"].append("Copy-storage migration required - may take longer")
        
        # TODO: Check memory availability on target host
        # TODO: Verify network connectivity between hosts
        
        return checks
    
    async def start_live_migration(
        self,
        system_id: str,
        source_host_id: str,
        target_host_id: str,
        migration_flags: dict[str, Any] | None = None,
        user_id: str = "system"
    ) -> str:
        """Start live migration of a system."""
        await self.init_migration_tables()
        
        # Merge flags with defaults
        flags = {**self.default_flags}
        if migration_flags:
            flags.update(migration_flags)
        
        # Generate migration ID
        migration_id = f"migration-{system_id}-{int(time.time())}"
        
        # Record migration start
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO hf_migrations 
                (id, system_id, source_host_id, target_host_id, migration_type, 
                 flags, status, started_at, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                migration_id,
                system_id,
                source_host_id,
                target_host_id,
                "live" if flags["live"] else "offline",
                json.dumps(flags),
                "starting",
                datetime.utcnow().isoformat(),
                user_id
            ))
            await db.commit()
        
        return migration_id
    
    async def perform_migration(
        self,
        migration_id: str,
        source_driver: LibvirtDriver,
        target_driver: LibvirtDriver
    ) -> bool:
        """Perform the actual migration."""
        try:
            # Get migration details
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    "SELECT system_id, flags FROM hf_migrations WHERE id = ?",
                    (migration_id,)
                )
                row = await cursor.fetchone()
                if not row:
                    raise ValueError(f"Migration {migration_id} not found")
                
                system_id, flags_json = row
                flags = json.loads(flags_json)
            
            # Update status to migrating
            await self._update_migration_status(migration_id, "migrating")
            
            # Get domain info from source
            domain_info = source_driver.get_system(system_id)
            if not domain_info:
                raise LibvirtError(f"System {system_id} not found on source host")
            
            # Start timing for downtime measurement
            start_time = time.time()
            
            # Perform migration based on flags
            if flags.get("live", True):
                success = await self._perform_live_migration(
                    source_driver, target_driver, system_id, flags
                )
            else:
                success = await self._perform_offline_migration(
                    source_driver, target_driver, system_id, flags
                )
            
            # Calculate downtime (for live migration, this is brief cutover time)
            downtime_ms = int((time.time() - start_time) * 1000)
            
            if success:
                await self._update_migration_status(
                    migration_id, "completed", downtime_ms=downtime_ms
                )
                return True
            else:
                await self._update_migration_status(
                    migration_id, "failed", error_message="Migration failed"
                )
                return False
                
        except Exception as e:
            await self._update_migration_status(
                migration_id, "failed", error_message=str(e)
            )
            raise
    
    async def _perform_live_migration(
        self,
        source_driver: LibvirtDriver,
        target_driver: LibvirtDriver,
        system_id: str,
        flags: dict[str, Any]
    ) -> bool:
        """Perform live migration using libvirt migrateToURI3."""
        try:
            # Build migration flags for libvirt
            migrate_flags = []
            
            if flags.get("live", True):
                migrate_flags.append("VIR_MIGRATE_LIVE")
            
            if flags.get("tunneled", True):
                migrate_flags.append("VIR_MIGRATE_PEER2PEER")
                migrate_flags.append("VIR_MIGRATE_TUNNELLED")
            
            if flags.get("compressed", False):
                migrate_flags.append("VIR_MIGRATE_COMPRESSED")
            
            if flags.get("auto_converge", True):
                migrate_flags.append("VIR_MIGRATE_AUTO_CONVERGE")
            
            if flags.get("copy_storage", False):
                migrate_flags.append("VIR_MIGRATE_NON_SHARED_DISK")
            
            # Build migration parameters
            params = {}
            
            if flags.get("bandwidth_mbps"):
                params["bandwidth"] = flags["bandwidth_mbps"]
            
            if flags.get("max_downtime_ms"):
                params["max_downtime"] = flags["max_downtime_ms"]
            
            # In a real implementation, this would call libvirt's migrateToURI3
            # For now, simulate the migration
            return await self._simulate_migration(source_driver, target_driver, system_id, flags)
            
        except Exception as e:
            raise LibvirtError(f"Live migration failed: {str(e)}")
    
    async def _perform_offline_migration(
        self,
        source_driver: LibvirtDriver,
        target_driver: LibvirtDriver,
        system_id: str,
        flags: dict[str, Any]
    ) -> bool:
        """Perform offline migration (power off, move, power on)."""
        try:
            # Power off on source
            source_driver.reset_system(system_id, "ForceOff")
            
            # Simulate migration
            success = await self._simulate_migration(source_driver, target_driver, system_id, flags)
            
            if success:
                # Power on at destination
                target_driver.reset_system(system_id, "On")
            
            return success
            
        except Exception as e:
            raise LibvirtError(f"Offline migration failed: {str(e)}")
    
    async def _simulate_migration(
        self,
        source_driver: LibvirtDriver,
        target_driver: LibvirtDriver,
        system_id: str,
        flags: dict[str, Any]
    ) -> bool:
        """Simulate migration for testing (replace with real libvirt calls)."""
        # In a real implementation, this would:
        # 1. Get domain XML from source
        # 2. Modify any host-specific paths
        # 3. Define domain on target
        # 4. Start migration via migrateToURI3
        # 5. Verify migration completion
        # 6. Clean up on source
        
        # For now, just simulate delay and success
        import asyncio
        await asyncio.sleep(2)  # Simulate migration time
        
        return True  # Simulate successful migration
    
    async def _update_migration_status(
        self,
        migration_id: str,
        status: str,
        downtime_ms: int | None = None,
        error_message: str | None = None
    ) -> None:
        """Update migration status in database."""
        async with aiosqlite.connect(self.db_path) as db:
            if status in ["completed", "failed"]:
                await db.execute("""
                    UPDATE hf_migrations 
                    SET status = ?, completed_at = ?, downtime_ms = ?, error_message = ?
                    WHERE id = ?
                """, (
                    status,
                    datetime.utcnow().isoformat(),
                    downtime_ms,
                    error_message,
                    migration_id
                ))
            else:
                await db.execute(
                    "UPDATE hf_migrations SET status = ? WHERE id = ?",
                    (status, migration_id)
                )
            await db.commit()
    
    async def get_migration_status(self, migration_id: str) -> dict[str, Any] | None:
        """Get migration status and details."""
        await self.init_migration_tables()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT system_id, source_host_id, target_host_id, migration_type,
                       status, started_at, completed_at, downtime_ms, error_message
                FROM hf_migrations WHERE id = ?
            """, (migration_id,))
            row = await cursor.fetchone()
            
            if row:
                return {
                    "id": migration_id,
                    "system_id": row[0],
                    "source_host_id": row[1],
                    "target_host_id": row[2],
                    "migration_type": row[3],
                    "status": row[4],
                    "started_at": row[5],
                    "completed_at": row[6],
                    "downtime_ms": row[7],
                    "error_message": row[8]
                }
            return None
    
    async def list_migrations(
        self, 
        system_id: str | None = None,
        limit: int = 100
    ) -> list[dict[str, Any]]:
        """List migrations, optionally filtered by system."""
        await self.init_migration_tables()
        
        query = """
            SELECT id, system_id, source_host_id, target_host_id, 
                   status, started_at, completed_at, downtime_ms
            FROM hf_migrations
        """
        params = []
        
        if system_id:
            query += " WHERE system_id = ?"
            params.append(system_id)
        
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params)
            rows = await cursor.fetchall()
            
            return [
                {
                    "id": row[0],
                    "system_id": row[1],
                    "source_host_id": row[2],
                    "target_host_id": row[3],
                    "status": row[4],
                    "started_at": row[5],
                    "completed_at": row[6],
                    "downtime_ms": row[7]
                }
                for row in rows
            ]


# Global service instance
migration_service = MigrationService()
