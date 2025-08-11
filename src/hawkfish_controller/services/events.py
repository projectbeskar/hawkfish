from __future__ import annotations

import asyncio
import json
import threading
import time
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import aiosqlite
import httpx


@dataclass
class Event:
    id: str
    type: str
    payload: dict[str, Any]


class EventBus:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[Event]] = []
        self._lock = asyncio.Lock()

    async def publish(self, event_type: str, payload: dict[str, Any]) -> Event:
        event = Event(id=str(uuid.uuid4()), type=event_type, payload=payload)
        async with self._lock:
            for q in list(self._subscribers):
                await q.put(event)
        return event

    async def subscribe(self) -> AsyncIterator[Event]:
        queue: asyncio.Queue[Event] = asyncio.Queue()
        async with self._lock:
            self._subscribers.append(queue)
        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            async with self._lock:
                if queue in self._subscribers:
                    self._subscribers.remove(queue)


class SubscriptionStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_lock = asyncio.Lock()

    async def init(self) -> None:
        async with self._init_lock:
            db = await aiosqlite.connect(self.db_path)
            try:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS hf_subscriptions (
                        id TEXT PRIMARY KEY,
                        destination TEXT NOT NULL,
                        event_types TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                # Migrate to add optional filter/secret columns if missing
                from contextlib import suppress

                with suppress(Exception):
                    await db.execute("ALTER TABLE hf_subscriptions ADD COLUMN system_ids TEXT")
                with suppress(Exception):
                    await db.execute("ALTER TABLE hf_subscriptions ADD COLUMN secret TEXT")

                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS hf_deadletters (
                        id TEXT PRIMARY KEY,
                        destination TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        error TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                # Outbound event queue
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS hf_outbox (
                        id TEXT PRIMARY KEY,
                        subscription_id TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        attempts INTEGER NOT NULL DEFAULT 0,
                        next_attempt_at TEXT NOT NULL,
                        last_error TEXT,
                        created_at TEXT NOT NULL
                    );
                    """
                )
                await db.commit()
            finally:
                await db.close()

    async def add(self, destination: str, event_types: list[str], system_ids: list[str] | None = None, secret: str | None = None) -> str:
        await self.init()
        sub_id = uuid.uuid4().hex
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        db = await aiosqlite.connect(self.db_path)
        try:
            from contextlib import suppress

            with suppress(Exception):
                await db.execute("ALTER TABLE hf_subscriptions ADD COLUMN system_ids TEXT")
            with suppress(Exception):
                await db.execute("ALTER TABLE hf_subscriptions ADD COLUMN secret TEXT")
            await db.execute(
                "INSERT INTO hf_subscriptions (id, destination, event_types, created_at, system_ids, secret) VALUES (?, ?, ?, ?, ?, ?)",
                (sub_id, destination, json.dumps(event_types), created_at, json.dumps(system_ids or []), secret or ""),
            )
            await db.commit()
        finally:
            await db.close()
        return sub_id

    async def list(self) -> list[dict[str, Any]]:
        await self.init()
        db = await aiosqlite.connect(self.db_path)
        try:
            try:
                cur = await db.execute(
                    "SELECT id, destination, event_types, created_at, system_ids, secret FROM hf_subscriptions ORDER BY created_at DESC"
                )
                rows = await cur.fetchall()
                await cur.close()
                return [
                    {
                        "Id": r[0],
                        "Destination": r[1],
                        "EventTypes": json.loads(r[2] or "[]"),
                        "CreatedAt": r[3],
                        "SystemIds": json.loads(r[4] or "[]"),
                        "Secret": r[5] or "",
                    }
                    for r in rows
                ]
            except Exception:
                # Fallback for older DBs without new columns
                cur = await db.execute(
                    "SELECT id, destination, event_types, created_at FROM hf_subscriptions ORDER BY created_at DESC"
                )
                rows = await cur.fetchall()
                await cur.close()
                return [
                    {
                        "Id": r[0],
                        "Destination": r[1],
                        "EventTypes": json.loads(r[2] or "[]"),
                        "CreatedAt": r[3],
                        "SystemIds": [],
                        "Secret": "",
                    }
                    for r in rows
                ]
        finally:
            await db.close()

    async def deliver(self, event: Event) -> None:
        """Queue events for durable delivery."""
        # ensure db directory exists
        import os
        from contextlib import suppress

        with suppress(Exception):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        subs = await self.list()
        if not subs:
            return
        
        # Queue matching subscriptions for async delivery
        for s in subs:
            event_types = s.get("EventTypes") or []
            if event_types and event.type not in event_types:
                continue
            system_ids = s.get("SystemIds") or []
            system_id = event.payload.get("systemId") if isinstance(event.payload, dict) else None
            if system_ids and system_id not in system_ids:
                continue
            
            # Create delivery payload
            payload = {"id": event.id, "type": event.type, "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **event.payload}
            secret = (s.get("Secret") or "").encode()
            if secret:
                import hashlib
                import hmac
                sig = hmac.new(secret, json.dumps(payload, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
                payload["_signature"] = f"sha256={sig}"
            
            # Queue for delivery
            await self._queue_delivery(s["Id"], payload)
        
        # Start delivery worker if not already running
        self._ensure_delivery_worker()

    async def _queue_delivery(self, subscription_id: str, payload: dict[str, Any]) -> None:
        """Add a delivery to the outbound queue."""
        await self.init()
        delivery_id = uuid.uuid4().hex
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO hf_outbox (id, subscription_id, payload, attempts, next_attempt_at, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (delivery_id, subscription_id, json.dumps(payload), 0, now, now),
            )
            await db.commit()

    def _ensure_delivery_worker(self) -> None:
        """Ensure the delivery worker is running."""
        if hasattr(self, "_worker_started") and self._worker_started:
            return
        
        self._worker_started = True
        
        def worker() -> None:
            import sqlite3
            import time as sync_time
            
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            
            while True:
                try:
                    # Get pending deliveries
                    now_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    cursor = conn.execute(
                        "SELECT id, subscription_id, payload, attempts FROM hf_outbox WHERE next_attempt_at <= ? ORDER BY created_at LIMIT 10",
                        (now_str,),
                    )
                    rows = cursor.fetchall()
                    
                    if not rows:
                        sync_time.sleep(5)  # No work, sleep
                        continue
                    
                    for row in rows:
                        delivery_id, sub_id, payload_json, attempts = row
                        self._process_delivery_sync(conn, delivery_id, sub_id, payload_json, attempts)
                    
                except Exception:  # pragma: no cover - error handling
                    sync_time.sleep(10)  # Error, back off
            
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def _process_delivery_sync(self, conn, delivery_id: str, subscription_id: str, payload_json: str, attempts: int) -> None:
        """Process a single delivery synchronously."""
        
        max_attempts = 5
        if attempts >= max_attempts:
            # Move to dead letters
            payload = json.loads(payload_json)
            conn.execute(
                "INSERT OR REPLACE INTO hf_deadletters (id, destination, event_type, payload, error, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (uuid.uuid4().hex, "unknown", payload.get("type", ""), payload_json, "Max attempts exceeded", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
            )
            conn.execute("DELETE FROM hf_outbox WHERE id=?", (delivery_id,))
            conn.commit()
            return
        
        try:
            # Get subscription details
            cursor = conn.execute("SELECT destination, secret FROM hf_subscriptions WHERE id=?", (subscription_id,))
            sub_row = cursor.fetchone()
            if not sub_row:
                # Subscription deleted, remove from queue
                conn.execute("DELETE FROM hf_outbox WHERE id=?", (delivery_id,))
                conn.commit()
                return
            
            destination, secret = sub_row
            payload = json.loads(payload_json)
            
            # Build headers
            headers = {"Content-Type": "application/json"}
            if secret and payload.get("_signature"):
                headers["X-HawkFish-Signature"] = payload.pop("_signature")
            
            # Make delivery
            with httpx.Client(timeout=10) as client:
                resp = client.post(destination, json=payload, headers=headers)
                if resp.status_code < 500:
                    # Success or permanent failure, remove from queue
                    conn.execute("DELETE FROM hf_outbox WHERE id=?", (delivery_id,))
                    conn.commit()
                    return
            
            # Retry with exponential backoff
            self._schedule_retry_sync(conn, delivery_id, attempts + 1)
            
        except Exception as exc:  # pragma: no cover - network
            self._schedule_retry_sync(conn, delivery_id, attempts + 1, str(exc))

    def _schedule_retry_sync(self, conn, delivery_id: str, attempts: int, error: str | None = None) -> None:
        """Schedule a retry with exponential backoff."""
        
        # Exponential backoff: 2^attempts seconds
        delay_seconds = 2 ** min(attempts, 8)  # Cap at 256 seconds
        next_attempt = time.time() + delay_seconds
        next_attempt_str = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(next_attempt))
        
        conn.execute(
            "UPDATE hf_outbox SET attempts=?, next_attempt_at=?, last_error=? WHERE id=?",
            (attempts, next_attempt_str, error, delivery_id),
        )
        conn.commit()

    async def _dead_letter(self, destination: str, event: Event, error: str) -> None:
        db = await aiosqlite.connect(self.db_path)
        try:
            await db.execute(
                "INSERT OR REPLACE INTO hf_deadletters (id, destination, event_type, payload, error, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    uuid.uuid4().hex,
                    destination,
                    event.type,
                    json.dumps(event.payload),
                    error,
                    time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                ),
            )
            await db.commit()
        finally:
            await db.close()


global_event_bus = EventBus()


async def publish_event(event_type: str, payload: dict[str, Any], subscriptions: SubscriptionStore) -> None:
    event = await global_event_bus.publish(event_type, payload)
    # deliver asynchronously via durable queue
    await subscriptions.deliver(event)


