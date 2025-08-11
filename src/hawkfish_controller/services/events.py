from __future__ import annotations

import asyncio
import json
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
        # ensure db directory exists
        import os
        from contextlib import suppress

        with suppress(Exception):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        subs = await self.list()
        if not subs:
            return
        async with httpx.AsyncClient(timeout=5) as client:
            for s in subs:
                event_types = s.get("EventTypes") or []
                if event_types and event.type not in event_types:
                    continue
                system_ids = s.get("SystemIds") or []
                system_id = event.payload.get("systemId") if isinstance(event.payload, dict) else None
                if system_ids and system_id not in system_ids:
                    continue
                payload = {"id": event.id, "type": event.type, "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **event.payload}
                headers = {}
                secret = (s.get("Secret") or "").encode()
                if secret:
                    import hashlib
                    import hmac
                    sig = hmac.new(secret, json.dumps(payload, separators=(",", ":")).encode(), hashlib.sha256).hexdigest()
                    headers["X-HawkFish-Signature"] = f"sha256={sig}"
                for attempt in range(5):
                    try:
                        resp = await client.post(s["Destination"], json=payload, headers=headers)
                        if resp.status_code < 500:
                            break
                    except Exception as exc:  # pragma: no cover - network
                        if attempt == 4:
                            await self._dead_letter(s["Destination"], event, str(exc))
                        await asyncio.sleep(2 ** attempt)

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
    # deliver synchronously to ensure deterministic behavior in tests
    await subscriptions.deliver(event)


