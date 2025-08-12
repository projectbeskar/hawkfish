from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from jsonschema import Draft7Validator, ValidationError

from ..config import settings
from ..services.events import SubscriptionStore, publish_event
from ..services.orchestrator import NodeSpec, create_node
from ..services.profiles import get_profile
from ..services.security import check_role
from ..services.tasks import TaskService
from .sessions import require_session

router = APIRouter(prefix="/redfish/v1/Oem/HawkFish/Batches", tags=["Batches"])


def get_task_service() -> TaskService:
    return TaskService(db_path=f"{settings.state_dir}/tasks.db")


_BATCH_SCHEMA = {
    "type": "object",
    "properties": {
        "NamePrefix": {"type": "string"},
        "StartIndex": {"type": "integer", "minimum": 0},
        "ZeroPad": {"type": "integer", "minimum": 0, "maximum": 6},
        "Count": {"type": "integer", "minimum": 1, "maximum": 1000},
        "ProfileId": {"type": "string"},
        "DeleteStorageOnDelete": {"type": "boolean"},
        "MaxConcurrency": {"type": "integer", "minimum": 1, "maximum": 32},
    },
    "required": ["ProfileId", "Count"],
}


@router.post("")
async def batch_create(body: dict, task_service: TaskService = Depends(get_task_service), session=Depends(require_session)):
    if not check_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        Draft7Validator(_BATCH_SCHEMA).validate(body)
    except ValidationError as exc:  # pragma: no cover - schema
        raise HTTPException(status_code=400, detail=f"Invalid batch: {exc.message}") from exc

    prefix = body.get("NamePrefix") or "node"
    start = int(body.get("StartIndex", 1))
    pad = int(body.get("ZeroPad", 2))
    count = int(body.get("Count", 1))
    profile_id = body.get("ProfileId")
    if not profile_id:
        raise HTTPException(status_code=400, detail="ProfileId required")
    prof = await get_profile(profile_id)
    if not prof:
        raise HTTPException(status_code=404, detail="Profile not found")

    subs = SubscriptionStore(db_path=f"{settings.state_dir}/events.db")

    async def job(task_id: str) -> None:
        await task_service.update(task_id, message=f"Batch starting: {count} nodes")
        sem = asyncio.Semaphore(int(body.get("MaxConcurrency", 3)))

        async def create_one(idx: int) -> None:
            name = f"{prefix}{str(idx).zfill(pad)}"
            spec = prof.spec.copy()
            spec["Name"] = name
            node_spec = NodeSpec(
                name=name,
                vcpus=int(spec.get("CPU", 1)),
                memory_mib=int(spec.get("MemoryMiB", 1024)),
                disk_gib=int(spec.get("DiskGiB", 10)),
                network=str(spec.get("Network", settings.network_name)),
                boot_primary=(spec.get("Boot", {}) or {}).get("Primary"),
                image_url=(spec.get("Image", {}) or {}).get("url"),
                cloud_init=spec.get("CloudInit"),
            )
            async with sem:
                await create_node(node_spec, task_service, subs)
                await publish_event("SystemCreated", {"systemId": name}, subs)

        await asyncio.gather(*[create_one(i) for i in range(start, start + count)])
        await task_service.update(task_id, message="Batch completed", end=True, percent=100, state="Completed")

    t = await task_service.run_background(name=f"Batch create {profile_id}", coro_factory=lambda tid: job(tid))
    return {"@odata.id": f"/redfish/v1/TaskService/Tasks/{t.id}"}


