from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response

from ..config import settings
from ..services.events import SubscriptionStore
from ..services.orchestrator import NodeSpec, create_node, delete_node
from ..services.security import check_role
from ..services.tasks import TaskService
from .sessions import require_session

router = APIRouter(prefix="/redfish/v1/Systems", tags=["Orchestrator"])


def get_task_service() -> TaskService:
    return TaskService(db_path=f"{settings.state_dir}/tasks.db")


def get_subs() -> SubscriptionStore:
    return SubscriptionStore(db_path=f"{settings.state_dir}/events.db")


@router.post("")
async def create_system(body: dict, task_service: TaskService = Depends(get_task_service), session=Depends(require_session)):
    if not check_role("admin", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    name = body.get("Name")
    if not name:
        raise HTTPException(status_code=400, detail="Name required")
    spec = NodeSpec(
        name=name,
        vcpus=int(body.get("CPU", 1)),
        memory_mib=int(body.get("MemoryMiB", 1024)),
        disk_gib=int(body.get("DiskGiB", 10)),
        network=str(body.get("Network", settings.network_name)),
        boot_primary=(body.get("Boot", {}) or {}).get("Primary"),
        image_url=(body.get("Image", {}) or {}).get("url"),
        cloud_init=body.get("CloudInit"),
    )
    task_id = await create_node(spec, task_service, get_subs())
    location = f"/redfish/v1/TaskService/Tasks/{task_id}"
    return Response(status_code=202, headers={"Location": location})


@router.delete("/{system_id}")
async def delete_system(system_id: str, delete_storage: bool = False, task_service: TaskService = Depends(get_task_service), session=Depends(require_session)):
    if not check_role("admin", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    task_id = await delete_node(system_id, delete_storage, task_service, get_subs())
    location = f"/redfish/v1/TaskService/Tasks/{task_id}"
    return Response(status_code=202, headers={"Location": location})


