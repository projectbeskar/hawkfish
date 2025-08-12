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
def list_systems(
    page: int = 1, 
    per_page: int = 50, 
    filter: str = "",
    driver: LibvirtDriver = Depends(get_driver), 
    session=Depends(require_session)
):
    """List systems with pagination and filtering."""
    systems = driver.list_systems()
    
    # Apply filtering
    if filter:
        filtered_systems = []
        for system in systems:
            # Simple filter format: key:value,key2:value2
            match = True
            for filter_part in filter.split(","):
                if ":" in filter_part:
                    key, value = filter_part.split(":", 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Check system properties and metadata
                    system_value = None
                    if key == "host":
                        # Would need to look up host from system metadata
                        system_value = "localhost"  # Placeholder
                    elif key == "tag":
                        # Would need to look up tags from system metadata
                        system_value = ""  # Placeholder
                    elif key == "power":
                        system_value = system.get("PowerState", "").lower()
                    elif key in system:
                        system_value = str(system[key]).lower()
                    
                    if system_value and value.lower() not in system_value:
                        match = False
                        break
            
            if match:
                filtered_systems.append(system)
        
        systems = filtered_systems
    
    # Apply pagination
    total_count = len(systems)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_systems = systems[start_idx:end_idx]
    
    members = [{"@odata.id": f"/redfish/v1/Systems/{s['Id']}"} for s in paginated_systems]
    
    # Build pagination links
    base_url = "/redfish/v1/Systems"
    pagination = {}
    
    if page > 1:
        pagination["@odata.prevLink"] = f"{base_url}?page={page-1}&per_page={per_page}"
        if filter:
            pagination["@odata.prevLink"] += f"&filter={filter}"
    
    if end_idx < total_count:
        pagination["@odata.nextLink"] = f"{base_url}?page={page+1}&per_page={per_page}"
        if filter:
            pagination["@odata.nextLink"] += f"&filter={filter}"
    
    result = {
        "@odata.id": "/redfish/v1/Systems",
        "@odata.type": "#ComputerSystemCollection.ComputerSystemCollection",
        "Name": "Systems Collection",
        "Members@odata.count": len(members),
        "Members": members,
    }
    result.update(pagination)
    
    return result


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


@router.post("/{system_id}/Actions/Oem.HawkFish.BootToPXE")
def boot_to_pxe(system_id: str, driver: LibvirtDriver = Depends(get_driver), session=Depends(require_session)):
    if not require_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    try:
        driver.set_boot_override(system_id, target="pxe", persist=False)
        return {"TaskState": "Completed"}
    except LibvirtError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.get("/{system_id}/EthernetInterfaces")
def list_ethernet_interfaces(system_id: str, driver: LibvirtDriver = Depends(get_driver), session=Depends(require_session)):
    """List EthernetInterfaces for a system."""
    system = driver.get_system(system_id)
    if system is None:
        return redfish_error("System not found", 404)
    
    interfaces = system.get("_EthernetInterfaceDetails", [])
    members = [{"@odata.id": iface["@odata.id"]} for iface in interfaces]
    
    return {
        "@odata.type": "#EthernetInterfaceCollection.EthernetInterfaceCollection",
        "@odata.id": f"/redfish/v1/Systems/{system_id}/EthernetInterfaces",
        "Name": "Ethernet Interfaces Collection",
        "Members@odata.count": len(members),
        "Members": members,
    }


@router.get("/{system_id}/EthernetInterfaces/{interface_id}")
def get_ethernet_interface(system_id: str, interface_id: str, response: Response, driver: LibvirtDriver = Depends(get_driver), session=Depends(require_session)):
    """Get details for a specific EthernetInterface."""
    system = driver.get_system(system_id)
    if system is None:
        return redfish_error("System not found", 404)
    
    interfaces = system.get("_EthernetInterfaceDetails", [])
    interface = None
    for iface in interfaces:
        if iface["Id"] == interface_id:
            interface = iface
            break
    
    if interface is None:
        return redfish_error("Interface not found", 404)
    
    # Add ETag for interface state
    etag = f'W/"{interface["MACAddress"]}-{interface["SpeedMbps"]}"'
    if response is not None:
        response.headers["ETag"] = etag
    
    # Remove internal fields and add proper type
    interface_copy = interface.copy()
    interface_copy["@odata.type"] = "#EthernetInterface.v1_9_0.EthernetInterface"
    
    return interface_copy


@router.post("/{system_id}/Actions/Oem.HawkFish.Migrate")
async def migrate_system_action(
    system_id: str,
    action_data: dict,
    session=Depends(require_session),
    driver: LibvirtDriver = Depends(get_driver)
):
    """Migrate a system to another host."""
    # Extract migration parameters
    target_host_id = action_data.get("TargetHostId")
    live_migration = action_data.get("LiveMigration", True)
    
    if not target_host_id:
        return redfish_error("MissingParameter", "TargetHostId is required", 400)
    
    try:
        # Get current system state to find source host
        systems = driver.list_systems()
        system = next((s for s in systems if s["Id"] == system_id), None)
        
        if not system:
            return redfish_error("ResourceNotFound", f"System {system_id} not found", 404)
        
        # For now, assume source host is default
        # In a real implementation, this would be tracked in the system metadata
        source_host_id = "localhost"  # Default/mock source host
        
        from ..services.hosts import migrate_system
        task_id = await migrate_system(
            system_id=system_id,
            source_host_id=source_host_id,
            target_host_id=target_host_id,
            live=live_migration
        )
        
        return {
            "@odata.type": "#Task.v1_7_0.Task",
            "Id": task_id,
            "Name": f"Migrate {system_id}",
            "TaskState": "Running",
            "TargetHostId": target_host_id,
            "LiveMigration": live_migration
        }
        
    except Exception as e:
        return redfish_error("OperationFailed", str(e), 500)


