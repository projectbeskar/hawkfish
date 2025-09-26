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
        # Try to get last applied settings first
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT attributes FROM hf_bios_applied 
                WHERE system_id = ?
                ORDER BY applied_at DESC LIMIT 1
            """, (system_id,))
            row = await cursor.fetchone()
            
            if row:
                return json.loads(row[0])
        
        # Fall back to defaults if no applied settings
        return self.default_attributes.copy()
    
    async def get_last_applied_attributes(self, system_id: str) -> dict[str, Any] | None:
        """Get the last applied BIOS attributes."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT attributes, applied_at, applied_by
                FROM hf_bios_applied 
                WHERE system_id = ?
                ORDER BY applied_at DESC LIMIT 1
            """, (system_id,))
            row = await cursor.fetchone()
            
            if row:
                return {
                    "attributes": json.loads(row[0]),
                    "applied_at": row[1],
                    "applied_by": row[2]
                }
            return None
    
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
        await self._validate_bios_attributes(attributes, system_id)
        
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
        
        attributes = pending["attributes"]
        
        async with aiosqlite.connect(self.db_path) as db:
            # Record applied settings
            await db.execute("""
                INSERT INTO hf_bios_applied
                (system_id, attributes, applied_at, applied_by)
                VALUES (?, ?, ?, ?)
            """, (
                system_id,
                json.dumps(attributes),
                datetime.utcnow().isoformat(),
                pending["staged_by"]
            ))
            
            # Remove from pending
            await db.execute(
                "DELETE FROM hf_bios_pending WHERE system_id = ?",
                (system_id,)
            )
            await db.commit()
        
        return attributes
    
    async def clear_pending_bios_changes(self, system_id: str) -> None:
        """Clear pending BIOS changes without applying."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM hf_bios_pending WHERE system_id = ?",
                (system_id,)
            )
            await db.commit()
    
    async def _validate_bios_attributes(self, attributes: dict[str, Any], system_id: str = "") -> None:
        """Validate BIOS attributes with HPE-style error messages."""
        from .message_registry import hpe_message_registry
        
        valid_boot_modes = {"Uefi", "LegacyBios"}
        valid_secure_boot = {"Enabled", "Disabled"}
        valid_boot_devices = {"Hdd", "Cd", "Pxe", "Usb", "Network"}
        
        if "BootMode" in attributes:
            if attributes["BootMode"] not in valid_boot_modes:
                raise BiosValidationError(
                    "Oem.Hpe.Bios.InvalidAttribute", 
                    ["BootMode", attributes["BootMode"]]
                )
        
        if "SecureBoot" in attributes:
            if attributes["SecureBoot"] not in valid_secure_boot:
                raise BiosValidationError(
                    "Oem.Hpe.Bios.InvalidAttribute",
                    ["SecureBoot", attributes["SecureBoot"]]
                )
            
            # SecureBoot only valid with UEFI
            current = await self.get_current_bios_attributes(system_id)
            boot_mode = attributes.get("BootMode", current.get("BootMode", "Uefi"))
            if attributes["SecureBoot"] == "Enabled" and boot_mode == "LegacyBios":
                raise BiosValidationError("Oem.Hpe.Bios.RequiresUefiForSecureBoot")
        
        if "PersistentBootConfigOrder" in attributes:
            boot_order = attributes["PersistentBootConfigOrder"]
            if not isinstance(boot_order, list):
                raise BiosValidationError(
                    "Oem.Hpe.Bios.InvalidAttribute",
                    ["PersistentBootConfigOrder", "must be a list"]
                )
            
            for device in boot_order:
                if device not in valid_boot_devices:
                    raise BiosValidationError(
                        "Oem.Hpe.Bios.InvalidAttribute",
                        ["PersistentBootConfigOrder", f"invalid device: {device}"]
                    )


class BiosValidationError(Exception):
    """Custom exception for BIOS validation errors with HPE message IDs."""
    
    def __init__(self, message_id: str, args: list = None):
        self.message_id = message_id
        self.args_list = args or []
        
        from .message_registry import hpe_message_registry
        message_info = hpe_message_registry.get_message(message_id, args)
        super().__init__(message_info["Message"])
        
        self.message_info = message_info


class BiosApplyTimeError(Exception):
    """Custom exception for ApplyTime validation errors."""
    
    def __init__(self, message_id: str, args: list = None):
        self.message_id = message_id
        self.args_list = args or []
        
        from .message_registry import hpe_message_registry
        message_info = hpe_message_registry.get_message(message_id, args)
        super().__init__(message_info["Message"])
        
        self.message_info = message_info


# Global service instance
bios_service = BiosService()
