from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Response
from fastapi.responses import StreamingResponse

from ..config import settings
from ..services.events import global_event_bus
from ..services.tasks import TaskService

router = APIRouter(tags=["Tasks", "Events"])


@router.get("/redfish/v1/TaskService")
def get_task_service_root():
    return {"Id": "TaskService", "Name": "Task Service", "Tasks": {"@odata.id": "/redfish/v1/TaskService/Tasks"}}


_task_service: TaskService | None = None


def get_task_service() -> TaskService:
    global _task_service
    if _task_service is None:
        _task_service = TaskService(db_path=f"{settings.state_dir}/tasks.db")
    return _task_service


@router.get("/redfish/v1/TaskService/Tasks")
async def list_tasks():
    tasks = await get_task_service().list()
    return {"Members": [{"@odata.id": f"/redfish/v1/TaskService/Tasks/{t.id}", "Name": t.name, "State": t.state, "PercentComplete": t.percent} for t in tasks]}


@router.get("/redfish/v1/TaskService/Tasks/{task_id}")
async def get_task(task_id: str):
    task = await get_task_service().get(task_id)
    if not task:
        return Response(status_code=404)
    return {"Id": task.id, "Name": task.name, "TaskState": task.state, "PercentComplete": task.percent, "Messages": task.messages, "StartTime": task.start_time, "EndTime": task.end_time}


async def sse_generator() -> AsyncGenerator[bytes, None]:
    async for event in global_event_bus.subscribe():
        payload = {
            "time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            **event.payload,
        }
        yield f"id: {event.id}\nevent: {event.type}\ndata: {json.dumps(payload)}\n\n".encode()


@router.get("/redfish/v1/EventService")
def get_event_service():
    return {"Id": "EventService", "Name": "Event Service", "Subscriptions": {"@odata.id": "/redfish/v1/EventService/Subscriptions"}}


@router.get("/redfish/v1/EventService/Subscriptions")
def list_subscriptions():
    return {"Members": []}


@router.get("/events/stream")
def event_stream():
    return StreamingResponse(sse_generator(), media_type="text/event-stream")


