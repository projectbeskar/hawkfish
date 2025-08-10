from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from ..config import settings
from ..drivers.libvirt_driver import LibvirtDriver, LibvirtError

router = APIRouter(prefix="/redfish/v1/Systems", tags=["Systems"])


def get_driver() -> LibvirtDriver:
    # Lazy-initialize driver per request to avoid global import issues in environments without libvirt
    return LibvirtDriver(settings.libvirt_uri)


@router.get("")
def list_systems(driver: LibvirtDriver = Depends(get_driver)):
    systems = driver.list_systems()
    members = [{"@odata.id": f"/redfish/v1/Systems/{s['Id']}"} for s in systems]
    return {
        "@odata.id": "/redfish/v1/Systems",
        "Name": "Systems Collection",
        "Members@odata.count": len(members),
        "Members": members,
    }


@router.get("/{system_id}")
def get_system(system_id: str, driver: LibvirtDriver = Depends(get_driver)):
    system = driver.get_system(system_id)
    if system is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="System not found")
    return system


@router.post("/{system_id}/Actions/ComputerSystem.Reset")
def system_reset(system_id: str, body: dict[str, Any], driver: LibvirtDriver = Depends(get_driver)):
    reset_type = body.get("ResetType")
    if not reset_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ResetType required")
    try:
        driver.reset_system(system_id, reset_type)
    except LibvirtError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"TaskState": "Completed"}


