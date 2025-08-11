from __future__ import annotations

import logging
import threading
import time
from contextlib import suppress
from dataclasses import dataclass
from typing import Any

from ..config import settings

logger = logging.getLogger(__name__)


@dataclass
class PooledConnection:
    """A pooled libvirt connection with metadata."""
    connection: Any  # libvirt connection object
    created_at: float
    last_used: float
    checkout_count: int
    is_healthy: bool


class LibvirtConnectionPool:
    """Thread-safe connection pool for libvirt connections."""
    
    def __init__(
        self,
        uri: str,
        min_connections: int = 1,
        max_connections: int = 10,
        ttl_seconds: int = 300,  # 5 minutes
        health_check_interval: int = 60,  # 1 minute
    ):
        self.uri = uri
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.ttl_seconds = ttl_seconds
        self.health_check_interval = health_check_interval
        
        self._pool: list[PooledConnection] = []
        self._lock = threading.RLock()
        self._libvirt = None
        self._last_health_check = 0.0
        self._total_checkouts = 0
        self._total_failures = 0
        self._total_reconnects = 0
        
        # Metrics
        self.metrics = {
            'pool_size': 0,
            'active_connections': 0,
            'checkout_count': 0,
            'failure_count': 0,
            'reconnect_count': 0,
        }
    
    def _import_libvirt(self):
        """Lazy import libvirt to avoid import errors in environments without it."""
        if self._libvirt is None:
            try:
                import libvirt  # type: ignore
                self._libvirt = libvirt
            except ImportError:
                self._libvirt = None
        return self._libvirt
    
    def _create_connection(self) -> Any | None:
        """Create a new libvirt connection."""
        libvirt = self._import_libvirt()
        if not libvirt:
            return None
        
        try:
            conn = libvirt.open(self.uri)
            return conn
        except Exception as exc:
            logger.error(f"Failed to create libvirt connection to {self.uri}: {exc}")
            self._total_failures += 1
            self.metrics['failure_count'] = self._total_failures
            return None
    
    def _is_connection_healthy(self, connection: Any) -> bool:
        """Check if a connection is still healthy."""
        if not connection:
            return False
        
        try:
            # Try a simple operation to test the connection
            connection.getHostname()
            return True
        except Exception:
            return False
    
    def _cleanup_expired_connections(self) -> None:
        """Remove expired connections from the pool."""
        now = time.time()
        to_remove = []
        
        for i, pooled_conn in enumerate(self._pool):
            if (now - pooled_conn.last_used) > self.ttl_seconds:
                to_remove.append(i)
                with suppress(Exception):
                    pooled_conn.connection.close()
        
        # Remove in reverse order to maintain indices
        for i in reversed(to_remove):
            del self._pool[i]
    
    def _ensure_minimum_connections(self) -> None:
        """Ensure we have at least min_connections in the pool."""
        current_size = len(self._pool)
        needed = self.min_connections - current_size
        
        for _ in range(needed):
            if len(self._pool) >= self.max_connections:
                break
            
            conn = self._create_connection()
            if conn:
                pooled_conn = PooledConnection(
                    connection=conn,
                    created_at=time.time(),
                    last_used=time.time(),
                    checkout_count=0,
                    is_healthy=True,
                )
                self._pool.append(pooled_conn)
    
    def _health_check(self) -> None:
        """Perform periodic health checks on pooled connections."""
        now = time.time()
        if (now - self._last_health_check) < self.health_check_interval:
            return
        
        self._last_health_check = now
        
        for pooled_conn in self._pool[:]:  # Copy list to avoid modification during iteration
            if not self._is_connection_healthy(pooled_conn.connection):
                pooled_conn.is_healthy = False
                self._pool.remove(pooled_conn)
                with suppress(Exception):
                    pooled_conn.connection.close()
                
                # Try to create a replacement if we're below minimum
                if len(self._pool) < self.min_connections:
                    replacement = self._create_connection()
                    if replacement:
                        new_pooled_conn = PooledConnection(
                            connection=replacement,
                            created_at=time.time(),
                            last_used=time.time(),
                            checkout_count=0,
                            is_healthy=True,
                        )
                        self._pool.append(new_pooled_conn)
                        self._total_reconnects += 1
                        self.metrics['reconnect_count'] = self._total_reconnects
    
    def get_connection(self) -> Any | None:
        """Get a connection from the pool."""
        with self._lock:
            self._health_check()
            self._cleanup_expired_connections()
            self._ensure_minimum_connections()
            
            # Try to find a healthy connection
            for pooled_conn in self._pool:
                if pooled_conn.is_healthy:
                    pooled_conn.last_used = time.time()
                    pooled_conn.checkout_count += 1
                    self._total_checkouts += 1
                    self.metrics['checkout_count'] = self._total_checkouts
                    self.metrics['pool_size'] = len(self._pool)
                    self.metrics['active_connections'] = len([c for c in self._pool if c.is_healthy])
                    return pooled_conn.connection
            
            # No healthy connections available, try to create a new one
            if len(self._pool) < self.max_connections:
                conn = self._create_connection()
                if conn:
                    pooled_conn = PooledConnection(
                        connection=conn,
                        created_at=time.time(),
                        last_used=time.time(),
                        checkout_count=1,
                        is_healthy=True,
                    )
                    self._pool.append(pooled_conn)
                    self._total_checkouts += 1
                    self.metrics['checkout_count'] = self._total_checkouts
                    self.metrics['pool_size'] = len(self._pool)
                    self.metrics['active_connections'] = len([c for c in self._pool if c.is_healthy])
                    return conn
            
            return None
    
    def return_connection(self, connection: Any) -> None:
        """Return a connection to the pool (currently a no-op since we don't track individual checkouts)."""
        # In a more sophisticated implementation, we might track individual checkouts
        # For now, connections remain in the pool and are managed by the health checker
        pass
    
    def close_all(self) -> None:
        """Close all connections in the pool."""
        with self._lock:
            for pooled_conn in self._pool:
                with suppress(Exception):
                    pooled_conn.connection.close()
            self._pool.clear()
            self.metrics['pool_size'] = 0
            self.metrics['active_connections'] = 0


class LibvirtPoolManager:
    """Global manager for libvirt connection pools."""
    
    def __init__(self):
        self._pools: dict[str, LibvirtConnectionPool] = {}
        self._lock = threading.RLock()
    
    def get_pool(self, uri: str) -> LibvirtConnectionPool:
        """Get or create a connection pool for the given URI."""
        with self._lock:
            if uri not in self._pools:
                # Get pool configuration from environment
                min_connections = int(getattr(settings, 'libvirt_pool_min', 1))
                max_connections = int(getattr(settings, 'libvirt_pool_max', 10))
                ttl_seconds = int(getattr(settings, 'libvirt_pool_ttl_sec', 300))
                
                self._pools[uri] = LibvirtConnectionPool(
                    uri=uri,
                    min_connections=min_connections,
                    max_connections=max_connections,
                    ttl_seconds=ttl_seconds,
                )
            
            return self._pools[uri]
    
    def get_connection(self, uri: str) -> Any | None:
        """Get a connection for the given URI."""
        pool = self.get_pool(uri)
        return pool.get_connection()
    
    def return_connection(self, uri: str, connection: Any) -> None:
        """Return a connection to the pool."""
        if uri in self._pools:
            self._pools[uri].return_connection(connection)
    
    def get_metrics(self) -> dict[str, Any]:
        """Get metrics for all pools."""
        with self._lock:
            metrics = {}
            for uri, pool in self._pools.items():
                pool_metrics = pool.metrics.copy()
                # Sanitize URI for metrics (remove credentials)
                safe_uri = uri.split('@')[-1] if '@' in uri else uri
                metrics[safe_uri] = pool_metrics
            return metrics
    
    def close_all(self) -> None:
        """Close all pools."""
        with self._lock:
            for pool in self._pools.values():
                pool.close_all()
            self._pools.clear()


# Global pool manager instance
pool_manager = LibvirtPoolManager()
