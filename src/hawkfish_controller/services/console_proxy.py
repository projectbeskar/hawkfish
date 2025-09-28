"""
WebSocket to TCP console proxy service.

Provides a websockify-style bridge for VNC, SPICE, and serial console access.
"""

import asyncio
import logging
import struct
import time
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from ..config import settings

logger = logging.getLogger(__name__)


class ConsoleProxy:
    """WebSocket to TCP proxy for console connections."""
    
    def __init__(self):
        self.active_connections: dict[str, dict[str, Any]] = {}
        self.connection_timeout = settings.console_idle_timeout or 600  # 10 minutes default
    
    async def handle_websocket_connection(self, websocket, token: str):
        """Handle a WebSocket console connection."""
        from .console import console_service
        
        try:
            # Validate and consume the token
            session = await console_service.get_session(token)
            if not session or not session.is_active:
                await websocket.close(code=4001, reason="Invalid or expired token")
                return
            
            # Mark token as used (single-use)
            await console_service.mark_token_used(token)
            
            logger.info(f"Console connection established for system {session.system_id} (protocol: {session.protocol})")
            
            # Store connection info
            connection_info = {
                "websocket": websocket,
                "session": session,
                "connected_at": time.time(),
                "last_activity": time.time()
            }
            self.active_connections[token] = connection_info
            
            try:
                if session.protocol == "vnc":
                    await self._handle_vnc_connection(websocket, session, connection_info)
                elif session.protocol == "serial":
                    await self._handle_serial_connection(websocket, session, connection_info)
                elif session.protocol == "spice":
                    await self._handle_spice_connection(websocket, session, connection_info)
                else:
                    await websocket.close(code=4002, reason="Unsupported protocol")
                    
            except ConnectionClosed:
                logger.info(f"Console connection closed for system {session.system_id}")
            except Exception as e:
                logger.error(f"Console proxy error for system {session.system_id}: {e}")
                await websocket.close(code=4003, reason="Internal proxy error")
            
        except Exception as e:
            logger.error(f"Failed to establish console connection: {e}")
            try:
                await websocket.close(code=4000, reason="Connection failed")
            except Exception:
                pass
        finally:
            # Clean up connection
            if token in self.active_connections:
                del self.active_connections[token]
    
    async def _handle_vnc_connection(self, websocket, session, connection_info):
        """Handle VNC protocol WebSocket connection."""
        # In a real implementation, this would:
        # 1. Connect to the VNC server (usually on libvirt domain)
        # 2. Handle VNC protocol handshake
        # 3. Bridge WebSocket frames to/from VNC TCP connection
        # 4. Handle VNC authentication if required
        
        # For now, send a simple message and wait
        await websocket.send("VNC console proxy not yet implemented")
        
        # Keep connection alive until client disconnects
        async for message in websocket:
            connection_info["last_activity"] = time.time()
            # Echo back for testing
            await websocket.send(f"Echo: {message}")
    
    async def _handle_serial_connection(self, websocket, session, connection_info):
        """Handle serial console WebSocket connection."""
        # In a real implementation, this would:
        # 1. Connect to the serial console (libvirt console or TCP socket)
        # 2. Bridge WebSocket text frames to/from serial connection
        # 3. Handle terminal emulation if needed
        
        # For now, provide a mock terminal
        await websocket.send("Serial console proxy - mock implementation\r\n")
        await websocket.send(f"Connected to system: {session.system_id}\r\n")
        await websocket.send("Type 'help' for available commands\r\n")
        await websocket.send("# ")
        
        async for message in websocket:
            connection_info["last_activity"] = time.time()
            
            # Simple command processing for demo
            command = message.strip()
            
            if command == "help":
                response = "Available commands:\r\n  help - Show this help\r\n  uptime - Show uptime\r\n  exit - Close connection\r\n# "
            elif command == "uptime":
                uptime = time.time() - connection_info["connected_at"]
                response = f"Console uptime: {uptime:.1f} seconds\r\n# "
            elif command == "exit":
                await websocket.send("Goodbye!\r\n")
                break
            else:
                response = f"Unknown command: {command}\r\n# "
            
            await websocket.send(response)
    
    async def _handle_spice_connection(self, websocket, session, connection_info):
        """Handle SPICE protocol WebSocket connection."""
        # SPICE protocol is more complex and would require:
        # 1. SPICE protocol implementation
        # 2. Connection to SPICE server
        # 3. Protocol translation between WebSocket and SPICE
        
        await websocket.send("SPICE console proxy not yet implemented")
        
        # Keep connection alive
        async for message in websocket:
            connection_info["last_activity"] = time.time()
            await websocket.send(f"SPICE Echo: {message}")
    
    async def cleanup_idle_connections(self):
        """Clean up idle console connections."""
        current_time = time.time()
        idle_tokens = []
        
        for token, connection_info in self.active_connections.items():
            if current_time - connection_info["last_activity"] > self.connection_timeout:
                idle_tokens.append(token)
        
        for token in idle_tokens:
            connection_info = self.active_connections[token]
            websocket = connection_info["websocket"]
            
            try:
                await websocket.close(code=4004, reason="Idle timeout")
                logger.info(f"Closed idle console connection for token {token}")
            except Exception:
                pass
            
            del self.active_connections[token]
    
    def get_connection_stats(self) -> dict[str, Any]:
        """Get statistics about active console connections."""
        current_time = time.time()
        stats = {
            "total_connections": len(self.active_connections),
            "connections_by_protocol": {},
            "oldest_connection_age": 0,
            "average_connection_age": 0
        }
        
        if self.active_connections:
            ages = []
            protocols = {}
            
            for connection_info in self.active_connections.values():
                age = current_time - connection_info["connected_at"]
                ages.append(age)
                
                protocol = connection_info["session"].protocol
                protocols[protocol] = protocols.get(protocol, 0) + 1
            
            stats["oldest_connection_age"] = max(ages)
            stats["average_connection_age"] = sum(ages) / len(ages)
            stats["connections_by_protocol"] = protocols
        
        return stats


# Global proxy instance
console_proxy = ConsoleProxy()


async def start_console_cleanup_task():
    """Start the background cleanup task for idle connections."""
    while True:
        try:
            await console_proxy.cleanup_idle_connections()
        except Exception as e:
            logger.error(f"Console cleanup task error: {e}")
        
        # Run cleanup every 5 minutes
        await asyncio.sleep(300)
