from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from jsonschema import Draft7Validator, ValidationError

from ..services.netprofiles import (
    create_netprofile,
    delete_netprofile,
    get_netprofile,
    list_netprofiles,
)
from ..services.security import require_role
from .sessions import require_session

router = APIRouter(prefix="/redfish/v1/Oem/HawkFish/NetworkProfiles", tags=["NetworkProfiles"])

NETPROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "Name": {"type": "string"},
        "LibvirtNetwork": {"type": "string"},
        "Bridge": {"type": "string"},
        "VLAN": {"type": "integer", "minimum": 1, "maximum": 4094},
        "MACPolicy": {"enum": ["auto", "fixed"]},
        "CountPerSystem": {"type": "integer", "minimum": 1, "maximum": 8},
        "CloudInitNetwork": {"type": "object"},
        "Labels": {"type": "object"},
    },
    "required": ["Name"],
}


@router.get("")
async def netprofiles_list(session=Depends(require_session)):
    """List all network profiles."""
    profiles = await list_netprofiles()
    return {
        "Members": [
            {
                "Id": p.id,
                "Name": p.name,
                "LibvirtNetwork": p.libvirt_network,
                "Bridge": p.bridge,
                "VLAN": p.vlan,
                "MACPolicy": p.mac_policy,
                "CountPerSystem": p.count_per_system,
                "CloudInitNetwork": p.cloud_init_network,
                "Labels": p.labels,
            }
            for p in profiles
        ]
    }


@router.get("/{profile_id}")
async def netprofiles_get(profile_id: str, session=Depends(require_session)):
    """Get details for a specific network profile."""
    profile = await get_netprofile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Network profile not found")
    
    return {
        "Id": profile.id,
        "Name": profile.name,
        "LibvirtNetwork": profile.libvirt_network,
        "Bridge": profile.bridge,
        "VLAN": profile.vlan,
        "MACPolicy": profile.mac_policy,
        "CountPerSystem": profile.count_per_system,
        "CloudInitNetwork": profile.cloud_init_network,
        "CreatedAt": profile.created_at,
        "Labels": profile.labels,
    }


@router.post("")
async def netprofiles_create(body: dict, session=Depends(require_session)):
    """Create a new network profile."""
    if not require_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        Draft7Validator(NETPROFILE_SCHEMA).validate(body)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid network profile: {exc.message}") from exc
    
    name = body["Name"]
    libvirt_network = body.get("LibvirtNetwork")
    bridge = body.get("Bridge")
    vlan = body.get("VLAN")
    mac_policy = body.get("MACPolicy", "auto")
    count_per_system = body.get("CountPerSystem", 1)
    cloud_init_network = body.get("CloudInitNetwork")
    labels = body.get("Labels", {})
    
    try:
        profile = await create_netprofile(
            name=name,
            libvirt_network=libvirt_network,
            bridge=bridge,
            vlan=vlan,
            mac_policy=mac_policy,
            count_per_system=count_per_system,
            cloud_init_network=cloud_init_network,
            labels=labels,
        )
        return {"Id": profile.id, "Name": profile.name}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to create network profile: {exc}") from exc


@router.delete("/{profile_id}")
async def netprofiles_delete(profile_id: str, session=Depends(require_session)):
    """Remove a network profile."""
    if not require_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    await delete_netprofile(profile_id)
    return {"TaskState": "Completed"}
