from __future__ import annotations

import asyncio
import json
import time
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import aiosqlite

TaskState = str  # "New" | "Running" | "Completed" | "Exception" | "Killed"


@dataclass
class Task:
    id: str
    name: str
    state: TaskState
    percent: int
    start_time: str
    end_time: str | None
    messages: list[str]


class TaskService:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        self._init_lock = asyncio.Lock()

    async def init(self) -> None:
        async with self._init_lock:
            db = await aiosqlite.connect(self.db_path)
            try:
                await db.execute(
                    """
                    CREATE TABLE IF NOT EXISTS hf_tasks (
                        id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        state TEXT NOT NULL,
                        percent INTEGER NOT NULL,
                        start_time TEXT NOT NULL,
                        end_time TEXT,
                        messages TEXT NOT NULL
                    )
                    """
                )
                await db.commit()
            finally:
                await db.close()

    async def create(self, name: str) -> Task:
        await self.init()
        task_id = uuid.uuid4().hex
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        task = Task(id=task_id, name=name, state="New", percent=0, start_time=now, end_time=None, messages=[])
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO hf_tasks (id, name, state, percent, start_time, end_time, messages) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (task.id, task.name, task.state, task.percent, task.start_time, task.end_time, json.dumps(task.messages)),
            )
            await db.commit()
        return task

    async def get(self, task_id: str) -> Task | None:
        await self.init()
        db = await aiosqlite.connect(self.db_path)
        try:
            cur = await db.execute(
                "SELECT id, name, state, percent, start_time, end_time, messages FROM hf_tasks WHERE id=?",
                (task_id,),
            )
            row = await cur.fetchone()
            await cur.close()
        finally:
            await db.close()
        if not row:
            return None
        return Task(
            id=row[0], name=row[1], state=row[2], percent=row[3], start_time=row[4], end_time=row[5], messages=json.loads(row[6] or "[]")
        )

    async def list(self) -> list[Task]:
        await self.init()
        db = await aiosqlite.connect(self.db_path)
        try:
            cur = await db.execute(
                "SELECT id, name, state, percent, start_time, end_time, messages FROM hf_tasks ORDER BY start_time DESC"
            )
            rows = await cur.fetchall()
            await cur.close()
        finally:
            await db.close()
        return [Task(id=r[0], name=r[1], state=r[2], percent=r[3], start_time=r[4], end_time=r[5], messages=json.loads(r[6] or "[]")) for r in rows]

    async def update(self, task_id: str, *, state: TaskState | None = None, percent: int | None = None, message: str | None = None, end: bool = False) -> None:
        await self.init()
        task = await self.get(task_id)
        if not task:
            return
        if state is not None:
            task.state = state
        if percent is not None:
            task.percent = percent
        if message:
            task.messages.append(message)
        if end:
            task.end_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE hf_tasks SET state=?, percent=?, end_time=?, messages=? WHERE id=?",
                (task.state, task.percent, task.end_time, json.dumps(task.messages), task_id),
            )
            await db.commit()

    async def run_background(self, name: str, coro_factory: Callable[[str], Awaitable[None]]) -> Task:
        task = await self.create(name)

        async def runner() -> None:
            try:
                await self.update(task.id, state="Running", percent=1)
                await coro_factory(task.id)
                await self.update(task.id, state="Completed", percent=100, end=True)
            except Exception as exc:  # pragma: no cover - error path
                await self.update(task.id, state="Exception", message=str(exc), end=True)

        asyncio.create_task(runner())
        return task


