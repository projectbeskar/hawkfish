from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from jsonschema import Draft7Validator, ValidationError

from ..services.events import SubscriptionStore, publish_event
from ..services.security import require_role
from ..services.snapshots import (
    create_snapshot,
    delete_snapshot,
    get_snapshot,
    list_snapshots,
    update_snapshot_state,
)
from ..services.tasks import TaskService
from .errors import redfish_error
from .sessions import require_session
from .systems import get_driver

router = APIRouter(tags=["Snapshots"])

SNAPSHOT_SCHEMA = {
    "type": "object",
    "properties": {
        "Name": {"type": "string"},
        "Description": {"type": "string"},
    },
}


@router.get("/redfish/v1/Systems/{system_id}/Oem/HawkFish/Snapshots")
async def list_system_snapshots(system_id: str, session=Depends(require_session)):
    """List all snapshots for a system."""
    # Verify system exists
    driver = get_driver()
    system = driver.get_system(system_id)
    if system is None:
        return redfish_error("System not found", 404)
    
    snapshots = await list_snapshots(system_id)
    members = [{"@odata.id": f"/redfish/v1/Systems/{system_id}/Oem/HawkFish/Snapshots/{snap.id}"} for snap in snapshots]
    
    return {
        "@odata.type": "#Collection.Collection",
        "@odata.id": f"/redfish/v1/Systems/{system_id}/Oem/HawkFish/Snapshots",
        "Name": "Snapshots Collection",
        "Members@odata.count": len(members),
        "Members": members,
    }


@router.get("/redfish/v1/Systems/{system_id}/Oem/HawkFish/Snapshots/{snapshot_id}")
async def get_system_snapshot(system_id: str, snapshot_id: str, response: Response, session=Depends(require_session)):
    """Get details for a specific snapshot."""
    snapshot = await get_snapshot(system_id, snapshot_id)
    if snapshot is None:
        return redfish_error("Snapshot not found", 404)
    
    # Add ETag for snapshot state
    etag = f'W/"{snapshot.state}-{snapshot.created_at}"'
    if response is not None:
        response.headers["ETag"] = etag
    
    return {
        "@odata.type": "#Oem.HawkFish.Snapshot",
        "@odata.id": f"/redfish/v1/Systems/{system_id}/Oem/HawkFish/Snapshots/{snapshot.id}",
        "Id": snapshot.id,
        "Name": snapshot.name,
        "Description": snapshot.description,
        "CreatedTime": snapshot.created_at,
        "SizeBytes": snapshot.size_bytes,
        "State": snapshot.state,
        "Actions": {
            "#Oem.HawkFish.Snapshot.Revert": {
                "target": f"/redfish/v1/Systems/{system_id}/Oem/HawkFish/Snapshots/{snapshot.id}/Actions/Oem.HawkFish.Snapshot.Revert"
            }
        }
    }


@router.post("/redfish/v1/Systems/{system_id}/Oem/HawkFish/Snapshots")
async def create_system_snapshot(system_id: str, body: dict, session=Depends(require_session)):
    """Create a new snapshot."""
    if not require_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # Validate input
    try:
        Draft7Validator(SNAPSHOT_SCHEMA).validate(body)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid snapshot: {exc.message}") from exc
    
    # Verify system exists
    driver = get_driver()
    system = driver.get_system(system_id)
    if system is None:
        return redfish_error("System not found", 404)
    
    name = body.get("Name")
    description = body.get("Description")
    
    # Create snapshot record
    snapshot = await create_snapshot(system_id, name, description)
    
    # Create background task to perform actual snapshot
    from ..config import settings
    task_service = TaskService(f"{settings.state_dir}/tasks.db")
    
    async def snapshot_task(task_id: str) -> None:
        try:
            await task_service.update(task_id, state="Running", percent=10, message="Creating snapshot")
            
            # Perform libvirt snapshot
            driver.create_snapshot(system_id, snapshot.libvirt_snapshot_name, description)
            
            await task_service.update(task_id, percent=90, message="Finalizing snapshot")
            await update_snapshot_state(snapshot.id, "Ready", size_bytes=0)  # Would calculate actual size
            
            await task_service.update(task_id, state="Completed", percent=100, message="Snapshot created")
            
            # Publish event
            subs = SubscriptionStore(db_path=f"{settings.state_dir}/events.db")
            await publish_event("SnapshotCreated", {"systemId": system_id, "snapshotId": snapshot.id, "name": snapshot.name}, subs)
            
        except Exception as exc:
            await update_snapshot_state(snapshot.id, "Failed", metadata={"error": str(exc)})
            await task_service.update(task_id, state="Exception", message=f"Failed: {exc}")
            raise
    
    task = await task_service.create(name=f"Create snapshot {snapshot.name}")
    
    # Start task in background
    import asyncio
    asyncio.create_task(snapshot_task(task.id))
    
    return {
        "@odata.id": f"/redfish/v1/Systems/{system_id}/Oem/HawkFish/Snapshots/{snapshot.id}",
        "TaskMonitor": f"/redfish/v1/TaskService/Tasks/{task.id}",
        "Id": snapshot.id,
        "Name": snapshot.name
    }, 202


@router.post("/redfish/v1/Systems/{system_id}/Oem/HawkFish/Snapshots/{snapshot_id}/Actions/Oem.HawkFish.Snapshot.Revert")
async def revert_system_snapshot(system_id: str, snapshot_id: str, session=Depends(require_session)):
    """Revert system to a snapshot."""
    if not require_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    snapshot = await get_snapshot(system_id, snapshot_id)
    if snapshot is None:
        return redfish_error("Snapshot not found", 404)
    
    if snapshot.state != "Ready":
        return redfish_error("Snapshot not ready for revert", 409)
    
    # Create background task to perform revert
    from ..config import settings
    task_service = TaskService(f"{settings.state_dir}/tasks.db")
    
    async def revert_task(task_id: str) -> None:
        try:
            await task_service.update(task_id, state="Running", percent=10, message="Reverting to snapshot")
            await update_snapshot_state(snapshot.id, "Reverting")
            
            # Perform libvirt revert
            driver = get_driver()
            driver.revert_snapshot(system_id, snapshot.libvirt_snapshot_name)
            
            await task_service.update(task_id, percent=90, message="Finalizing revert")
            await update_snapshot_state(snapshot.id, "Ready")
            
            await task_service.update(task_id, state="Completed", percent=100, message="Revert completed")
            
            # Publish event
            subs = SubscriptionStore(db_path=f"{settings.state_dir}/events.db")
            await publish_event("SnapshotReverted", {"systemId": system_id, "snapshotId": snapshot.id, "name": snapshot.name}, subs)
            
        except Exception as exc:
            await update_snapshot_state(snapshot.id, "Ready")  # Reset state on failure
            await task_service.update(task_id, state="Exception", message=f"Failed: {exc}")
            raise
    
    task = await task_service.create(name=f"Revert to snapshot {snapshot.name}")
    
    # Start task in background
    import asyncio
    asyncio.create_task(revert_task(task.id))
    
    return {
        "TaskMonitor": f"/redfish/v1/TaskService/Tasks/{task.id}",
        "TaskState": "Running"
    }, 202


@router.delete("/redfish/v1/Systems/{system_id}/Oem/HawkFish/Snapshots/{snapshot_id}")
async def delete_system_snapshot(system_id: str, snapshot_id: str, session=Depends(require_session)):
    """Delete a snapshot."""
    if not require_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    snapshot = await get_snapshot(system_id, snapshot_id)
    if snapshot is None:
        return redfish_error("Snapshot not found", 404)
    
    # Create background task to perform deletion
    from ..config import settings
    task_service = TaskService(f"{settings.state_dir}/tasks.db")
    
    async def delete_task(task_id: str) -> None:
        try:
            await task_service.update(task_id, state="Running", percent=10, message="Deleting snapshot")
            
            # Delete from libvirt
            driver = get_driver()
            driver.delete_libvirt_snapshot(system_id, snapshot.libvirt_snapshot_name)
            
            await task_service.update(task_id, percent=90, message="Cleaning up records")
            await delete_snapshot(snapshot.id)
            
            await task_service.update(task_id, state="Completed", percent=100, message="Snapshot deleted")
            
            # Publish event
            subs = SubscriptionStore(db_path=f"{settings.state_dir}/events.db")
            await publish_event("SnapshotDeleted", {"systemId": system_id, "snapshotId": snapshot.id, "name": snapshot.name}, subs)
            
        except Exception as exc:
            await task_service.update(task_id, state="Exception", message=f"Failed: {exc}")
            raise
    
    task = await task_service.create(name=f"Delete snapshot {snapshot.name}")
    
    # Start task in background
    import asyncio
    asyncio.create_task(delete_task(task.id))
    
    return {
        "TaskMonitor": f"/redfish/v1/TaskService/Tasks/{task.id}",
        "TaskState": "Running"
    }, 202
