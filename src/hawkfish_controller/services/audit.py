from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite

from ..config import settings

logger = logging.getLogger(__name__)


class AuditLogger:
    """Service for logging state-changing operations for audit purposes."""
    
    def __init__(self, db_path: str | None = None):
        self.db_path = Path(db_path or settings.state_dir) / "audit.db"
        self._initialized = False
    
    async def init(self) -> None:
        """Initialize audit database."""
        if self._initialized:
            return
        
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id TEXT,
                    session_id TEXT,
                    client_ip TEXT,
                    action TEXT NOT NULL,
                    resource_type TEXT NOT NULL,
                    resource_id TEXT,
                    method TEXT NOT NULL,
                    path TEXT NOT NULL,
                    status_code INTEGER,
                    success BOOLEAN NOT NULL,
                    details TEXT,
                    request_body TEXT,
                    response_body TEXT,
                    duration_ms INTEGER
                )
            """)
            
            # Create index for efficient querying
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_timestamp 
                ON audit_log(timestamp)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_user_action 
                ON audit_log(user_id, action)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_resource 
                ON audit_log(resource_type, resource_id)
            """)
            
            await db.commit()
        
        self._initialized = True
        logger.info(f"Audit logging initialized: {self.db_path}")
    
    async def log_action(
        self,
        action: str,
        resource_type: str,
        method: str,
        path: str,
        success: bool,
        resource_id: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
        client_ip: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
        request_body: dict[str, Any] | None = None,
        response_body: dict[str, Any] | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """Log an audit event.
        
        Args:
            action: Action performed (e.g., "create", "update", "delete", "power_on")
            resource_type: Type of resource (e.g., "system", "profile", "image")
            method: HTTP method
            path: Request path
            success: Whether the operation succeeded
            resource_id: ID of the affected resource
            user_id: User performing the action
            session_id: Session ID
            client_ip: Client IP address
            status_code: HTTP status code
            details: Additional operation details
            request_body: Request payload (will be JSON encoded)
            response_body: Response payload (will be JSON encoded)
            duration_ms: Operation duration in milliseconds
        """
        await self.init()
        
        timestamp = datetime.utcnow().isoformat()
        
        # Serialize complex objects
        details_json = json.dumps(details) if details else None
        request_json = json.dumps(request_body) if request_body else None
        response_json = json.dumps(response_body) if response_body else None
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO audit_log (
                    timestamp, user_id, session_id, client_ip, action,
                    resource_type, resource_id, method, path, status_code,
                    success, details, request_body, response_body, duration_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                timestamp, user_id, session_id, client_ip, action,
                resource_type, resource_id, method, path, status_code,
                success, details_json, request_json, response_json, duration_ms
            ))
            await db.commit()
        
        logger.debug(f"Audit log: {action} {resource_type}:{resource_id} by {user_id} -> {success}")
    
    async def get_audit_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        action: str | None = None,
        start_time: str | None = None,
        end_time: str | None = None,
        success: bool | None = None,
    ) -> dict[str, Any]:
        """Retrieve audit logs with filtering.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            user_id: Filter by user ID
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            action: Filter by action
            start_time: Filter by start timestamp (ISO format)
            end_time: Filter by end timestamp (ISO format)
            success: Filter by success status
            
        Returns:
            Dictionary with logs and metadata
        """
        await self.init()
        
        # Build WHERE clause
        conditions = []
        params = []
        
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        
        if resource_type:
            conditions.append("resource_type = ?")
            params.append(resource_type)
        
        if resource_id:
            conditions.append("resource_id = ?")
            params.append(resource_id)
        
        if action:
            conditions.append("action = ?")
            params.append(action)
        
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)
        
        if success is not None:
            conditions.append("success = ?")
            params.append(success)
        
        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""
        
        async with aiosqlite.connect(self.db_path) as db:
            # Get total count
            count_query = f"SELECT COUNT(*) FROM audit_log{where_clause}"
            async with db.execute(count_query, params) as cursor:
                total_count = (await cursor.fetchone())[0]
            
            # Get logs
            query = f"""
                SELECT timestamp, user_id, session_id, client_ip, action,
                       resource_type, resource_id, method, path, status_code,
                       success, details, duration_ms
                FROM audit_log{where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """
            
            logs = []
            async with db.execute(query, params + [limit, offset]) as cursor:
                async for row in cursor:
                    log_entry = {
                        "timestamp": row[0],
                        "user_id": row[1],
                        "session_id": row[2],
                        "client_ip": row[3],
                        "action": row[4],
                        "resource_type": row[5],
                        "resource_id": row[6],
                        "method": row[7],
                        "path": row[8],
                        "status_code": row[9],
                        "success": bool(row[10]),
                        "details": json.loads(row[11]) if row[11] else None,
                        "duration_ms": row[12],
                    }
                    logs.append(log_entry)
        
        return {
            "logs": logs,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": total_count > (offset + len(logs))
        }
    
    async def get_audit_stats(self) -> dict[str, Any]:
        """Get audit log statistics."""
        await self.init()
        
        async with aiosqlite.connect(self.db_path) as db:
            stats = {}
            
            # Total entries
            async with db.execute("SELECT COUNT(*) FROM audit_log") as cursor:
                stats["total_entries"] = (await cursor.fetchone())[0]
            
            # Success/failure counts
            async with db.execute("SELECT success, COUNT(*) FROM audit_log GROUP BY success") as cursor:
                success_stats = {bool(row[0]): row[1] async for row in cursor}
                stats["successful_operations"] = success_stats.get(True, 0)
                stats["failed_operations"] = success_stats.get(False, 0)
            
            # Top actions
            async with db.execute("""
                SELECT action, COUNT(*) as count 
                FROM audit_log 
                GROUP BY action 
                ORDER BY count DESC 
                LIMIT 10
            """) as cursor:
                stats["top_actions"] = {row[0]: row[1] async for row in cursor}
            
            # Top users
            async with db.execute("""
                SELECT user_id, COUNT(*) as count 
                FROM audit_log 
                WHERE user_id IS NOT NULL
                GROUP BY user_id 
                ORDER BY count DESC 
                LIMIT 10
            """) as cursor:
                stats["top_users"] = {row[0]: row[1] async for row in cursor}
            
            # Recent activity (last 24 hours)
            async with db.execute("""
                SELECT COUNT(*) 
                FROM audit_log 
                WHERE timestamp >= datetime('now', '-1 day')
            """) as cursor:
                stats["recent_activity_24h"] = (await cursor.fetchone())[0]
        
        return stats


# Global audit logger instance
audit_logger = AuditLogger()
