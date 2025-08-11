from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status

from ..config import settings
from ..drivers.libvirt_driver import LibvirtDriver, LibvirtError
from ..services.events import SubscriptionStore, publish_event
from ..services.metrics import POWER_ACTIONS
from ..services.security import require_role
from .errors import redfish_error
from .sessions import require_session

router = APIRouter(prefix="/redfish/v1/Systems", tags=["Systems"])


def get_driver() -> LibvirtDriver:
    # Lazy-initialize driver per request to avoid global import issues in environments without libvirt
    return LibvirtDriver(settings.libvirt_uri)


@router.get("")
def list_systems(driver: LibvirtDriver = Depends(get_driver), session=Depends(require_session)):
    systems = driver.list_systems()
    members = [{"@odata.id": f"/redfish/v1/Systems/{s['Id']}"} for s in systems]
    return {
        "@odata.id": "/redfish/v1/Systems",
        "Name": "Systems Collection",
        "Members@odata.count": len(members),
        "Members": members,
    }


@router.get("/{system_id}", response_model=None)
def get_system(system_id: str, response: Response, driver: LibvirtDriver = Depends(get_driver), session=Depends(require_session)):
    system = driver.get_system(system_id)
    if system is None:
        return redfish_error("System not found", 404)
    # weak ETag using power, cpu, mem; can be replaced by persisted version
    etag = f"W/\"{system.get('PowerState')}-{system.get('ProcessorSummary',{}).get('Count',0)}-{system.get('MemorySummary',{}).get('TotalSystemMemoryGiB',0)}\""
    if response is not None:
        response.headers["ETag"] = etag
    return system


@router.post("/{system_id}/Actions/ComputerSystem.Reset")
def system_reset(system_id: str, body: dict[str, Any], driver: LibvirtDriver = Depends(get_driver), session=Depends(require_session)):
    if not require_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    reset_type = body.get("ResetType")
    if not reset_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ResetType required")
    try:
        driver.reset_system(system_id, reset_type)
        # fire event (ensure loop context via anyio)
        from anyio import from_thread as _from_thread
        subs = SubscriptionStore(db_path=f"{settings.state_dir}/events.db")
        _from_thread.run(publish_event, "PowerStateChanged", {"systemId": system_id, "details": {"reset": reset_type}}, subs)
        POWER_ACTIONS.labels(reset_type=reset_type, result="success").inc()
    except LibvirtError as exc:
        POWER_ACTIONS.labels(reset_type=reset_type, result="error").inc()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"TaskState": "Completed"}


@router.post("/{system_id}/Actions/ComputerSystem.SetDefaultBootOrder")
def set_default_boot_order(system_id: str, driver: LibvirtDriver = Depends(get_driver), session=Depends(require_session)):
    if not require_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    # For now, set to HDD persistently
    try:
        driver.set_boot_override(system_id, target="hdd", persist=True)
    except LibvirtError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"TaskState": "Completed"}


@router.patch("/{system_id}")
def set_boot_override(system_id: str, body: dict[str, Any], driver: LibvirtDriver = Depends(get_driver), session=Depends(require_session), if_match: str | None = Header(default=None, alias="If-Match")):
    if not require_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    boot = body.get("Boot") or {}
    target = boot.get("BootSourceOverrideTarget")
    enabled = boot.get("BootSourceOverrideEnabled", "Once")
    if not target:
        raise HTTPException(status_code=400, detail="Boot.BootSourceOverrideTarget required")
    # simple If-Match enforcement: require header when provided
    if if_match is not None and if_match.strip() == "*":
        pass
    elif if_match is not None:
        current = driver.get_system(system_id)
        if not current:
            return redfish_error("System not found", 404)
        current_etag = f"W/\"{current.get('PowerState')}-{current.get('ProcessorSummary',{}).get('Count',0)}-{current.get('MemorySummary',{}).get('TotalSystemMemoryGiB',0)}\""
        if if_match != current_etag:
            return redfish_error("ETag mismatch", 412)
    persist = enabled.lower() == "continuous"
    try:
        driver.set_boot_override(system_id, target=target, persist=persist)
        from anyio import from_thread as _from_thread
        subs = SubscriptionStore(db_path=f"{settings.state_dir}/events.db")
        _from_thread.run(publish_event, "BootOverrideSet", {"systemId": system_id, "details": {"target": target, "persist": persist}}, subs)
    except LibvirtError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"TaskState": "Completed"}


