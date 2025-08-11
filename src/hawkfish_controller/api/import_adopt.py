from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from ..config import settings
from ..drivers.libvirt_driver import LibvirtDriver
from ..services.adoption import create_adoption, get_adoption_by_system_id, list_adoptions
from ..services.hosts import get_default_host, get_host
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
async def import_adopt(body: dict, dry_run: bool = Query(default=False), driver: LibvirtDriver = Depends(get_driver), session=Depends(require_session)):
    if not require_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    domains = body.get("Domains") or []
    host_id = body.get("HostId")  # Optional, defaults to default host
    
    if dry_run:
        return {"Adopted": [d.get("Name") for d in domains]}
    
    # Get target host
    if host_id:
        host = await get_host(host_id)
        if not host:
            raise HTTPException(status_code=404, detail="Host not found")
    else:
        host = await get_default_host()
        if not host:
            raise HTTPException(status_code=400, detail="No hosts available")
    
    adopted = []
    for domain_spec in domains:
        domain_name = domain_spec.get("Name")
        if not domain_name:
            continue
        
        # Check if already adopted
        existing = await get_adoption_by_system_id(domain_name)
        if existing:
            continue
        
        # Create adoption mapping (using domain name as both system_id and libvirt_uuid for simplicity)
        # In a real implementation, we'd query libvirt to get the actual UUID
        try:
            await create_adoption(
                host_id=host.id,
                libvirt_uuid=f"fake-uuid-{domain_name}",  # Would be real UUID from libvirt
                system_id=domain_name,
                tags=domain_spec.get("Tags", {}),
            )
            adopted.append(domain_name)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to adopt {domain_name}: {exc}") from exc
    
    return {"Adopted": adopted}


@router.get("/Adoptions")
async def list_adoption_mappings(session=Depends(require_session)):
    """List all adoption mappings."""
    adoptions = await list_adoptions()
    return {
        "Members": [
            {
                "Id": a.id,
                "HostId": a.host_id,
                "LibvirtUUID": a.libvirt_uuid,
                "SystemId": a.system_id,
                "AdoptedAt": a.adopted_at,
                "Tags": a.tags,
            }
            for a in adoptions
        ]
    }


