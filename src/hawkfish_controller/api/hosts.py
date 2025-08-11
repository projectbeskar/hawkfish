from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from jsonschema import Draft7Validator, ValidationError

from ..services.hosts import add_host, delete_host, get_host, list_hosts
from ..services.security import require_role
from .sessions import require_session

router = APIRouter(prefix="/redfish/v1/Oem/HawkFish/Hosts", tags=["Hosts"])

HOST_SCHEMA = {
    "type": "object",
    "properties": {
        "URI": {"type": "string"},
        "Name": {"type": "string"},
        "Labels": {"type": "object"},
    },
    "required": ["URI", "Name"],
}


@router.get("")
async def hosts_list(session=Depends(require_session)):
    """List all hosts in the pool."""
    hosts = await list_hosts()
    return {
        "Members": [
            {
                "Id": h.id,
                "URI": h.uri,
                "Name": h.name,
                "Labels": h.labels,
                "Capacity": h.capacity,
                "Allocated": h.allocated,
                "State": h.state,
            }
            for h in hosts
        ]
    }


@router.get("/{host_id}")
async def hosts_get(host_id: str, session=Depends(require_session)):
    """Get details for a specific host."""
    host = await get_host(host_id)
    if not host:
        raise HTTPException(status_code=404, detail="Host not found")
    
    return {
        "Id": host.id,
        "URI": host.uri,
        "Name": host.name,
        "Labels": host.labels,
        "Capacity": host.capacity,
        "Allocated": host.allocated,
        "State": host.state,
        "CreatedAt": host.created_at,
    }


@router.post("")
async def hosts_create(body: dict, session=Depends(require_session)):
    """Add a new host to the pool."""
    if not require_role("admin", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        Draft7Validator(HOST_SCHEMA).validate(body)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid host: {exc.message}") from exc
    
    uri = body["URI"]
    name = body["Name"]
    labels = body.get("Labels", {})
    
    try:
        host = await add_host(uri, name, labels)
        return {"Id": host.id, "URI": host.uri, "Name": host.name}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to add host: {exc}") from exc


@router.delete("/{host_id}")
async def hosts_delete(host_id: str, session=Depends(require_session)):
    """Remove a host from the pool."""
    if not require_role("admin", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    await delete_host(host_id)
    return {"TaskState": "Completed"}
