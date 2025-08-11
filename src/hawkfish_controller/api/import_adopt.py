from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import settings
from ..drivers.libvirt_driver import LibvirtDriver
from ..services.security import require_role
from .sessions import require_session

router = APIRouter(prefix="/redfish/v1/Oem/HawkFish/Import", tags=["Import"])


def get_driver() -> LibvirtDriver:
    return LibvirtDriver(settings.libvirt_uri)


@router.get("/Scan")
def import_scan(driver: LibvirtDriver = Depends(get_driver), session=Depends(require_session)):
    # For now, just return all domains as candidates
    systems = driver.list_systems()
    return {"Candidates": [{"Name": s["Id"]} for s in systems]}


@router.post("/Adopt")
def import_adopt(body: dict, dry_run: bool = Query(default=False), driver: LibvirtDriver = Depends(get_driver), session=Depends(require_session)):
    if not require_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    domains = body.get("Domains") or []
    if dry_run:
        return {"Adopted": [d.get("Name") for d in domains]}
    # Persist mapping in future; for now, assume adopted
    return {"Adopted": [d.get("Name") for d in domains]}


