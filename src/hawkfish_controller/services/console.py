from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
import time
from dataclasses import dataclass
from typing import Any

import aiosqlite

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class ConsoleSession:
    """A console session with one-time token."""
    token: str
    system_id: str
    protocol: str  # "vnc", "spice", "serial"
    user_id: str
    created_at: float
    expires_at: float
    is_active: bool = False


class ConsoleService:
    """Service for managing console access via WebSocket proxy."""
    
    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or f"{settings.state_dir}/hawkfish.db"
        self._initialized = False
        self._active_sessions: dict[str, ConsoleSession] = {}
    
    async def init(self) -> None:
        """Initialize console sessions table."""
        if self._initialized:
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS hf_console_sessions (
                    token TEXT PRIMARY KEY,
                    system_id TEXT NOT NULL,
                    protocol TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    is_active BOOLEAN DEFAULT FALSE
                )
            """)
            await db.commit()
        
        self._initialized = True
        logger.info("Console service initialized")
    
    async def create_session(
        self,
        system_id: str,
        protocol: str,
        user_id: str,
        ttl_seconds: int = 300  # 5 minutes default
    ) -> ConsoleSession:
        """Create a new console session with one-time token."""
        await self.init()
        
        if protocol not in ["vnc", "spice", "serial"]:
            raise ValueError(f"Unsupported protocol: {protocol}")
        
        # Generate secure one-time token
        token = self._generate_session_token(system_id, user_id)
        
        now = time.time()
        expires_at = now + ttl_seconds
        
        session = ConsoleSession(
            token=token,
            system_id=system_id,
            protocol=protocol,
            user_id=user_id,
            created_at=now,
            expires_at=expires_at
        )
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO hf_console_sessions 
                (token, system_id, protocol, user_id, created_at, expires_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                token, system_id, protocol, user_id, now, expires_at, False
            ))
            await db.commit()
        
        self._active_sessions[token] = session
        
        logger.info(f"Created console session for {system_id} ({protocol}) - token: {token[:8]}...")
        return session
    
    async def get_session(self, token: str) -> ConsoleSession | None:
        """Get console session by token."""
        await self.init()
        
        # Check in-memory cache first
        if token in self._active_sessions:
            session = self._active_sessions[token]
            if time.time() < session.expires_at:
                return session
            else:
                # Expired - remove from cache
                del self._active_sessions[token]
        
        # Check database
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("""
                SELECT token, system_id, protocol, user_id, created_at, expires_at, is_active
                FROM hf_console_sessions
                WHERE token = ?
            """, (token,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None
                
                session = ConsoleSession(
                    token=row[0],
                    system_id=row[1],
                    protocol=row[2],
                    user_id=row[3],
                    created_at=row[4],
                    expires_at=row[5],
                    is_active=bool(row[6])
                )
                
                # Check if expired
                if time.time() >= session.expires_at:
                    await self.revoke_session(token)
                    return None
                
                return session
    
    async def activate_session(self, token: str) -> bool:
        """Mark a session as active (in use)."""
        await self.init()
        
        session = await self.get_session(token)
        if not session:
            return False
        
        if session.is_active:
            return False  # Already active
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE hf_console_sessions 
                SET is_active = TRUE 
                WHERE token = ?
            """, (token,))
            updated = cursor.rowcount > 0
            await db.commit()
            
            if updated and token in self._active_sessions:
                self._active_sessions[token].is_active = True
            
            return updated
    
    async def revoke_session(self, token: str) -> bool:
        """Revoke a console session."""
        await self.init()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM hf_console_sessions WHERE token = ?
            """, (token,))
            deleted = cursor.rowcount > 0
            await db.commit()
            
            if token in self._active_sessions:
                del self._active_sessions[token]
            
            if deleted:
                logger.info(f"Revoked console session: {token[:8]}...")
            
            return deleted
    
    async def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions from database."""
        await self.init()
        
        now = time.time()
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                DELETE FROM hf_console_sessions WHERE expires_at <= ?
            """, (now,))
            deleted_count = cursor.rowcount
            await db.commit()
        
        # Clean up in-memory cache
        expired_tokens = [
            token for token, session in self._active_sessions.items()
            if now >= session.expires_at
        ]
        for token in expired_tokens:
            del self._active_sessions[token]
        
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired console sessions")
        
        return deleted_count
    
    async def list_active_sessions(self, system_id: str | None = None) -> list[ConsoleSession]:
        """List active console sessions."""
        await self.init()
        
        sessions = []
        query = """
            SELECT token, system_id, protocol, user_id, created_at, expires_at, is_active
            FROM hf_console_sessions
            WHERE expires_at > ?
        """
        params = [time.time()]
        
        if system_id:
            query += " AND system_id = ?"
            params.append(system_id)
        
        query += " ORDER BY created_at DESC"
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(query, params) as cursor:
                async for row in cursor:
                    sessions.append(ConsoleSession(
                        token=row[0],
                        system_id=row[1],
                        protocol=row[2],
                        user_id=row[3],
                        created_at=row[4],
                        expires_at=row[5],
                        is_active=bool(row[6])
                    ))
        
        return sessions
    
    def _generate_session_token(self, system_id: str, user_id: str) -> str:
        """Generate a secure one-time token for console access."""
        # Combine random data with system/user context
        random_data = secrets.token_bytes(32)
        context_data = f"{system_id}:{user_id}:{time.time()}".encode()
        
        # Create HMAC-style token
        token_data = hashlib.sha256(random_data + context_data).hexdigest()
        
        # Make it URL-safe and shorter
        return token_data[:32]
    
    async def get_console_connection_info(self, system_id: str, protocol: str) -> dict[str, Any]:
        """Get connection info for console access (libvirt graphics settings)."""
        # This would typically query libvirt for graphics configuration
        # For now, return mock data based on protocol
        
        if protocol == "vnc":
            return {
                "host": "localhost",
                "port": 5900,  # VNC port
                "protocol": "vnc",
                "display": ":0"
            }
        elif protocol == "spice":
            return {
                "host": "localhost", 
                "port": 5901,  # SPICE port
                "protocol": "spice",
                "tls": False
            }
        elif protocol == "serial":
            return {
                "protocol": "serial",
                "device": "/dev/pts/0",  # Serial console device
                "baud": 115200
            }
        else:
            raise ValueError(f"Unsupported protocol: {protocol}")


# Global console service instance
console_service = ConsoleService()
