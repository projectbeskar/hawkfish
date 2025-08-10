from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter(tags=["Tasks", "Events"])


@router.get("/redfish/v1/TaskService")
def get_task_service():
    return {"Id": "TaskService", "Name": "Task Service", "Tasks": {"@odata.id": "/redfish/v1/TaskService/Tasks"}}


@router.get("/redfish/v1/TaskService/Tasks")
def list_tasks():
    return {"Members": []}


async def sse_generator() -> AsyncGenerator[bytes, None]:
    for i in range(3):
        yield f"data: {{\"event\": \"tick\", \"n\": {i}}}\n\n".encode()
        await asyncio.sleep(0.1)


@router.get("/redfish/v1/EventService")
def get_event_service():
    return {"Id": "EventService", "Name": "Event Service", "Subscriptions": {"@odata.id": "/redfish/v1/EventService/Subscriptions"}}


@router.get("/redfish/v1/EventService/Subscriptions")
def list_subscriptions():
    return {"Members": []}


@router.get("/events/stream")
def event_stream():
    return StreamingResponse(sse_generator(), media_type="text/event-stream")


