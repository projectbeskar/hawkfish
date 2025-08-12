"""
BIOS/UEFI settings management with ApplyTime staging support.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import aiosqlite

from ..config import settings


class BiosService:
    """Service for managing BIOS/UEFI settings with staging support."""
    
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or f"{settings.state_dir}/hawkfish.db"
        
        # Default BIOS attributes
        self.default_attributes = {
            "BootMode": "Uefi",
            "SecureBoot": "Disabled", 
            "PersistentBootConfigOrder": ["Hdd", "Cd", "Pxe"]
        }
    
    async def get_current_bios_attributes(self, system_id: str) -> dict[str, Any]:
        """Get current BIOS attributes for a system."""
        # TODO: Read from libvirt domain XML in a real implementation
        # For now, return defaults
        return self.default_attributes.copy()
    
    async def get_pending_bios_changes(self, system_id: str) -> dict[str, Any] | None:
        """Get pending BIOS changes for a system."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT attributes, apply_time, staged_at, staged_by
                FROM hf_bios_pending 
                WHERE system_id = ?
            """, (system_id,))
            row = await cursor.fetchone()
            
            if row:
                return {
                    "attributes": json.loads(row[0]),
                    "apply_time": row[1],
                    "staged_at": row[2],
                    "staged_by": row[3]
                }
            return None
    
    async def stage_bios_changes(
        self, 
        system_id: str, 
        attributes: dict[str, Any], 
        apply_time: str,
        user_id: str
    ) -> None:
        """Stage BIOS changes for later application."""
        # Validate attributes
        await self._validate_bios_attributes(attributes)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO hf_bios_pending
                (system_id, attributes, apply_time, staged_at, staged_by)
                VALUES (?, ?, ?, ?, ?)
            """, (
                system_id,
                json.dumps(attributes),
                apply_time,
                datetime.utcnow().isoformat(),
                user_id
            ))
            await db.commit()
    
    async def apply_pending_bios_changes(self, system_id: str) -> dict[str, Any] | None:
        """Apply pending BIOS changes and remove from staging."""
        pending = await self.get_pending_bios_changes(system_id)
        if not pending:
            return None
        
        # TODO: Apply changes to libvirt domain XML
        # This would include:
        # - Switching firmware (OVMF vs SeaBIOS)
        # - Setting secure boot varstore
        # - Configuring boot order
        
        # Remove from pending
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM hf_bios_pending WHERE system_id = ?",
                (system_id,)
            )
            await db.commit()
        
        return pending["attributes"]
    
    async def clear_pending_bios_changes(self, system_id: str) -> None:
        """Clear pending BIOS changes without applying."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM hf_bios_pending WHERE system_id = ?",
                (system_id,)
            )
            await db.commit()
    
    async def _validate_bios_attributes(self, attributes: dict[str, Any]) -> None:
        """Validate BIOS attributes."""
        valid_boot_modes = {"Uefi", "LegacyBios"}
        valid_secure_boot = {"Enabled", "Disabled"}
        valid_boot_devices = {"Hdd", "Cd", "Pxe", "Usb", "Network"}
        
        if "BootMode" in attributes:
            if attributes["BootMode"] not in valid_boot_modes:
                raise ValueError(f"Invalid BootMode: {attributes['BootMode']}")
        
        if "SecureBoot" in attributes:
            if attributes["SecureBoot"] not in valid_secure_boot:
                raise ValueError(f"Invalid SecureBoot: {attributes['SecureBoot']}")
            
            # SecureBoot only valid with UEFI
            current = await self.get_current_bios_attributes(attributes.get("system_id", ""))
            boot_mode = attributes.get("BootMode", current.get("BootMode", "Uefi"))
            if attributes["SecureBoot"] == "Enabled" and boot_mode == "LegacyBios":
                raise ValueError("SecureBoot requires UEFI boot mode")
        
        if "PersistentBootConfigOrder" in attributes:
            boot_order = attributes["PersistentBootConfigOrder"]
            if not isinstance(boot_order, list):
                raise ValueError("PersistentBootConfigOrder must be a list")
            
            for device in boot_order:
                if device not in valid_boot_devices:
                    raise ValueError(f"Invalid boot device: {device}")


# Global service instance
bios_service = BiosService()
