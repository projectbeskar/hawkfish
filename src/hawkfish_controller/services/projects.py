from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import aiosqlite

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class Project:
    """A multi-tenant project with resources and quotas."""
    id: str
    name: str
    description: str
    created_at: str
    labels: dict[str, Any]
    quotas: dict[str, int]
    usage: dict[str, int]
    default_persona: str = "generic"


@dataclass
class ProjectMember:
    """A project member with assigned role."""
    user_id: str
    project_id: str
    role: str  # admin, operator, viewer
    assigned_at: str
    assigned_by: str


class ProjectStore:
    """Service for managing multi-tenant projects."""
    
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or f"{settings.state_dir}/hawkfish.db"
        self._initialized = False
    
    async def init(self) -> None:
        """Initialize project database tables."""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            # Projects table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS hf_projects (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    labels TEXT,
                    quotas TEXT,
                    default_persona TEXT DEFAULT 'generic'
                )
            """)
            
            # Project members and roles
            await db.execute("""
                CREATE TABLE IF NOT EXISTS hf_project_roles (
                    user_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    assigned_at TEXT NOT NULL,
                    assigned_by TEXT,
                    PRIMARY KEY (user_id, project_id),
                    FOREIGN KEY (project_id) REFERENCES hf_projects (id) ON DELETE CASCADE
                )
            """)
            
            # Project quotas (optional separate table for complex quotas)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS hf_project_quotas (
                    project_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    quota_value INTEGER NOT NULL,
                    updated_at TEXT NOT NULL,
                    updated_by TEXT,
                    PRIMARY KEY (project_id, resource_type),
                    FOREIGN KEY (project_id) REFERENCES hf_projects (id) ON DELETE CASCADE
                )
            """)
            
            # Usage tracking
            await db.execute("""
                CREATE TABLE IF NOT EXISTS hf_usage (
                    project_id TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    current_usage INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (project_id, resource_type),
                    FOREIGN KEY (project_id) REFERENCES hf_projects (id) ON DELETE CASCADE
                )
            """)
            
            # System persona overrides
            await db.execute("""
                CREATE TABLE IF NOT EXISTS hf_system_personas (
                    system_id TEXT PRIMARY KEY,
                    persona TEXT NOT NULL DEFAULT 'generic',
                    updated_at TEXT NOT NULL,
                    updated_by TEXT
                )
            """)
            
            # BIOS settings staging for ApplyTime=OnReset
            await db.execute("""
                CREATE TABLE IF NOT EXISTS hf_bios_pending (
                    system_id TEXT PRIMARY KEY,
                    attributes TEXT NOT NULL,
                    apply_time TEXT NOT NULL,
                    staged_at TEXT NOT NULL,
                    staged_by TEXT
                )
            """)
            
            # BIOS applied settings history
            await db.execute("""
                CREATE TABLE IF NOT EXISTS hf_bios_applied (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    system_id TEXT NOT NULL,
                    attributes TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    applied_by TEXT
                )
            """)
            
            # Create default project if it doesn't exist
            await db.execute("""
                INSERT OR IGNORE INTO hf_projects (id, name, description, created_at, labels, quotas)
                VALUES (
                    'default',
                    'Default Project',
                    'Default project for existing resources',
                    ?, 
                    '{}',
                    '{"vcpus": 1000, "memory_gib": 1000, "disk_gib": 10000, "systems": 100}'
                )
            """, (datetime.utcnow().isoformat(),))
            
            await db.commit()
        
        self._initialized = True
        logger.info("Project store initialized")
    
    async def create_project(
        self,
        project_id: str,
        name: str,
        description: str = "",
        labels: dict[str, Any] | None = None,
        quotas: dict[str, int] | None = None
    ) -> Project:
        """Create a new project."""
        await self.init()
        
        labels = labels or {}
        quotas = quotas or {
            "vcpus": 100,
            "memory_gib": 500,
            "disk_gib": 1000,
            "systems": 50
        }
        
        created_at = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO hf_projects (id, name, description, created_at, labels, quotas)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                project_id, name, description, created_at,
                json.dumps(labels), json.dumps(quotas)
            ))
            
            # Initialize usage tracking
            for resource_type in quotas:
                await db.execute("""
                    INSERT INTO hf_usage (project_id, resource_type, current_usage, updated_at)
                    VALUES (?, ?, 0, ?)
                """, (project_id, resource_type, created_at))
            
            await db.commit()
        
        logger.info(f"Created project: {project_id} ({name})")
        return Project(
            id=project_id,
            name=name,
            description=description,
            created_at=created_at,
            labels=labels,
            quotas=quotas,
            usage={k: 0 for k in quotas}
        )
    
    async def get_project(self, project_id: str) -> Project | None:
        """Get project by ID."""
        await self.init()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT id, name, description, created_at, labels, quotas
                FROM hf_projects WHERE id = ?
            """, (project_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                
                # Get current usage
                usage = {}
                async with db.execute("""
                    SELECT resource_type, current_usage
                    FROM hf_usage WHERE project_id = ?
                """, (project_id,)) as usage_cursor:
                    async for usage_row in usage_cursor:
                        usage[usage_row[0]] = usage_row[1]
                
                return Project(
                    id=row[0],
                    name=row[1],
                    description=row[2] or "",
                    created_at=row[3],
                    labels=json.loads(row[4]) if row[4] else {},
                    quotas=json.loads(row[5]) if row[5] else {},
                    usage=usage
                )
    
    async def list_projects(self, user_id: str | None = None) -> list[Project]:
        """List projects. If user_id provided, only return projects the user has access to."""
        await self.init()
        
        async with aiosqlite.connect(self.db_path) as db:
            if user_id:
                # Get projects where user has a role
                query = """
                    SELECT DISTINCT p.id, p.name, p.description, p.created_at, p.labels, p.quotas
                    FROM hf_projects p
                    LEFT JOIN hf_project_roles pr ON p.id = pr.project_id
                    WHERE pr.user_id = ? OR p.id = 'default'
                    ORDER BY p.name
                """
                params = (user_id,)
            else:
                # Admin view: all projects
                query = """
                    SELECT id, name, description, created_at, labels, quotas
                    FROM hf_projects
                    ORDER BY name
                """
                params = ()
            
            projects = []
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    project_id = row[0]
                    
                    # Get usage for this project
                    usage = {}
                    async with db.execute("""
                        SELECT resource_type, current_usage
                        FROM hf_usage WHERE project_id = ?
                    """, (project_id,)) as usage_cursor:
                        async for usage_row in usage_cursor:
                            usage[usage_row[0]] = usage_row[1]
                    
                    projects.append(Project(
                        id=row[0],
                        name=row[1],
                        description=row[2] or "",
                        created_at=row[3],
                        labels=json.loads(row[4]) if row[4] else {},
                        quotas=json.loads(row[5]) if row[5] else {},
                        usage=usage
                    ))
            
            return projects
    
    async def delete_project(self, project_id: str) -> bool:
        """Delete a project. Cannot delete default project."""
        await self.init()
        
        if project_id == "default":
            raise ValueError("Cannot delete default project")
        
        async with aiosqlite.connect(self.db_path) as db:
            # Check if project has any resources
            resource_count = 0
            for table in ["hf_systems", "hf_profiles", "hf_images"]:
                try:
                    async with db.execute(f"""
                        SELECT COUNT(*) FROM {table} WHERE project_id = ?
                    """, (project_id,)) as cursor:
                        count = (await cursor.fetchone())[0]
                        resource_count += count
                except Exception:
                    # Table might not have project_id column yet
                    pass
            
            if resource_count > 0:
                raise ValueError(f"Project has {resource_count} resources. Remove them first.")
            
            # Delete project (cascades to roles, quotas, usage)
            cursor = await db.execute("DELETE FROM hf_projects WHERE id = ?", (project_id,))
            deleted = cursor.rowcount > 0
            await db.commit()
            
            if deleted:
                logger.info(f"Deleted project: {project_id}")
            
            return deleted
    
    async def add_member(
        self,
        project_id: str,
        user_id: str,
        role: str,
        assigned_by: str
    ) -> ProjectMember:
        """Add a member to a project with a role."""
        await self.init()
        
        if role not in ["admin", "operator", "viewer"]:
            raise ValueError(f"Invalid role: {role}")
        
        assigned_at = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO hf_project_roles 
                (user_id, project_id, role, assigned_at, assigned_by)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, project_id, role, assigned_at, assigned_by))
            await db.commit()
        
        logger.info(f"Added member {user_id} to project {project_id} with role {role}")
        return ProjectMember(
            user_id=user_id,
            project_id=project_id,
            role=role,
            assigned_at=assigned_at,
            assigned_by=assigned_by
        )
    
    async def remove_member(self, project_id: str, user_id: str) -> bool:
        """Remove a member from a project."""
        await self.init()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM hf_project_roles 
                WHERE project_id = ? AND user_id = ?
            """, (project_id, user_id))
            removed = cursor.rowcount > 0
            await db.commit()
            
            if removed:
                logger.info(f"Removed member {user_id} from project {project_id}")
            
            return removed
    
    async def list_members(self, project_id: str) -> list[ProjectMember]:
        """List members of a project."""
        await self.init()
        
        async with aiosqlite.connect(self.db_path) as db:
            members = []
            async with db.execute("""
                SELECT user_id, project_id, role, assigned_at, assigned_by
                FROM hf_project_roles
                WHERE project_id = ?
                ORDER BY assigned_at
            """, (project_id,)) as cursor:
                async for row in cursor:
                    members.append(ProjectMember(
                        user_id=row[0],
                        project_id=row[1],
                        role=row[2],
                        assigned_at=row[3],
                        assigned_by=row[4] or ""
                    ))
            
            return members
    
    async def get_user_role(self, project_id: str, user_id: str) -> str | None:
        """Get user's role in a project."""
        await self.init()
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT role FROM hf_project_roles
                WHERE project_id = ? AND user_id = ?
            """, (project_id, user_id)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
    
    async def check_quota(
        self,
        project_id: str,
        resource_type: str,
        requested_amount: int
    ) -> tuple[bool, dict[str, Any]]:
        """Check if requested resource would exceed quota.
        
        Returns (allowed, quota_info) where quota_info contains current/quota/available.
        """
        await self.init()
        
        project = await self.get_project(project_id)
        if not project:
            return False, {"error": "Project not found"}
        
        current_usage = project.usage.get(resource_type, 0)
        quota_limit = project.quotas.get(resource_type, 0)
        available = quota_limit - current_usage
        
        quota_info = {
            "resource_type": resource_type,
            "current_usage": current_usage,
            "quota_limit": quota_limit,
            "available": available,
            "requested": requested_amount
        }
        
        allowed = (current_usage + requested_amount) <= quota_limit
        return allowed, quota_info
    
    async def update_usage(
        self,
        project_id: str,
        resource_type: str,
        delta: int
    ) -> None:
        """Update resource usage for a project (delta can be positive or negative)."""
        await self.init()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO hf_usage (project_id, resource_type, current_usage, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(project_id, resource_type) DO UPDATE SET
                current_usage = MAX(0, current_usage + ?),
                updated_at = ?
            """, (
                project_id, resource_type, max(0, delta), datetime.utcnow().isoformat(),
                delta, datetime.utcnow().isoformat()
            ))
            await db.commit()
    
    async def set_quotas(
        self,
        project_id: str,
        quotas: dict[str, int],
        updated_by: str
    ) -> None:
        """Set project quotas."""
        await self.init()
        
        updated_at = datetime.utcnow().isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            # Update main project quotas
            await db.execute("""
                UPDATE hf_projects SET quotas = ? WHERE id = ?
            """, (json.dumps(quotas), project_id))
            
            # Update detailed quota table
            for resource_type, quota_value in quotas.items():
                await db.execute("""
                    INSERT OR REPLACE INTO hf_project_quotas
                    (project_id, resource_type, quota_value, updated_at, updated_by)
                    VALUES (?, ?, ?, ?, ?)
                """, (project_id, resource_type, quota_value, updated_at, updated_by))
                
                # Ensure usage tracking exists
                await db.execute("""
                    INSERT OR IGNORE INTO hf_usage
                    (project_id, resource_type, current_usage, updated_at)
                    VALUES (?, ?, 0, ?)
                """, (project_id, resource_type, updated_at))
            
            await db.commit()
        
        logger.info(f"Updated quotas for project {project_id}: {quotas}")


# Global project store instance
project_store = ProjectStore()
