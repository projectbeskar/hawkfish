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

    async def add(self, destination: str, event_types: list[str]) -> str:
        await self.init()
        sub_id = uuid.uuid4().hex
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        db = await aiosqlite.connect(self.db_path)
        try:
            await db.execute(
                "INSERT INTO hf_subscriptions (id, destination, event_types, created_at) VALUES (?, ?, ?, ?)",
                (sub_id, destination, json.dumps(event_types), created_at),
            )
            await db.commit()
        finally:
            await db.close()
        return sub_id

    async def list(self) -> list[dict[str, Any]]:
        await self.init()
        db = await aiosqlite.connect(self.db_path)
        try:
            cur = await db.execute(
                "SELECT id, destination, event_types, created_at FROM hf_subscriptions ORDER BY created_at DESC"
            )
            rows = await cur.fetchall()
            await cur.close()
        finally:
            await db.close()
        return [
            {
                "Id": r[0],
                "Destination": r[1],
                "EventTypes": json.loads(r[2] or "[]"),
                "CreatedAt": r[3],
            }
            for r in rows
        ]

    async def deliver(self, event: Event) -> None:
        subs = await self.list()
        if not subs:
            return
        async with httpx.AsyncClient(timeout=5) as client:
            for s in subs:
                if s.get("EventTypes") and event.type not in s["EventTypes"]:
                    continue
                payload = {"id": event.id, "type": event.type, "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **event.payload}
                for attempt in range(5):
                    try:
                        resp = await client.post(s["Destination"], json=payload)
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
    # fire-and-forget delivery
    asyncio.create_task(subscriptions.deliver(event))


