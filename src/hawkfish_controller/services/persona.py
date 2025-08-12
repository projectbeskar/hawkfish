"""
Persona management service for handling system-level persona assignments.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import aiosqlite

from ..config import settings
from ..persona.registry import persona_registry


class PersonaService:
    """Service for managing persona assignments."""
    
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or f"{settings.state_dir}/hawkfish.db"
    
    async def get_system_persona(self, system_id: str, project_id: str = "default") -> str:
        """Get the effective persona for a system."""
        async with aiosqlite.connect(self.db_path) as db:
            # Check for system-specific override
            cursor = await db.execute(
                "SELECT persona FROM hf_system_personas WHERE system_id = ?",
                (system_id,)
            )
            row = await cursor.fetchone()
            if row:
                return row[0]
            
            # Fall back to project default
            cursor = await db.execute(
                "SELECT default_persona FROM hf_projects WHERE id = ?",
                (project_id,)
            )
            row = await cursor.fetchone()
            if row and row[0]:
                return row[0]
            
            # Final fallback
            return "generic"
    
    async def set_system_persona(self, system_id: str, persona: str, user_id: str) -> None:
        """Set a system-specific persona override."""
        # Validate persona exists
        if persona != "generic" and not persona_registry.get_plugin(persona):
            raise ValueError(f"Unknown persona: {persona}")
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO hf_system_personas 
                (system_id, persona, updated_at, updated_by)
                VALUES (?, ?, ?, ?)
            """, (system_id, persona, datetime.utcnow().isoformat(), user_id))
            await db.commit()
    
    async def remove_system_persona(self, system_id: str) -> None:
        """Remove system-specific persona override (fall back to project default)."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM hf_system_personas WHERE system_id = ?",
                (system_id,)
            )
            await db.commit()
    
    async def get_project_default_persona(self, project_id: str) -> str:
        """Get the default persona for a project."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT default_persona FROM hf_projects WHERE id = ?",
                (project_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row and row[0] else "generic"
    
    async def set_project_default_persona(self, project_id: str, persona: str) -> None:
        """Set the default persona for a project."""
        # Validate persona exists
        if persona != "generic" and not persona_registry.get_plugin(persona):
            raise ValueError(f"Unknown persona: {persona}")
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE hf_projects SET default_persona = ? WHERE id = ?",
                (persona, project_id)
            )
            await db.commit()


# Global service instance
persona_service = PersonaService()
