from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..services.security import get_current_session, check_role, require_role
from ..services.storage import storage_service
from .errors import redfish_error

# Storage Pools router
pools_router = APIRouter(prefix="/redfish/v1/Oem/HawkFish/Storage/Pools", tags=["Storage"])

# Storage Volumes router  
volumes_router = APIRouter(prefix="/redfish/v1/Oem/HawkFish/Storage/Volumes", tags=["Storage"])

# System Volume Actions router
system_volumes_router = APIRouter(prefix="/redfish/v1/Systems", tags=["Storage"])


class PoolCreate(BaseModel):
    name: str
    type: str = "dir"  # dir, nfs, lvm, iscsi
    target_path: str
    host_id: str
    capacity_gb: int = 100
    autostart: bool = True
    config: dict = {}


class VolumeCreate(BaseModel):
    name: str
    pool_id: str
    capacity_gb: int
    format: str = "qcow2"  # qcow2, raw, vmdk
    project_id: str = "default"
    labels: dict = {}


class VolumeAttach(BaseModel):
    volume_id: str
    device: str = "vdb"  # Virtual device name


class VolumeResize(BaseModel):
    capacity_gb: int


# Storage Pools endpoints
@pools_router.get("")
async def list_pools(
    host_id: str = None,
    session=Depends(get_current_session),
):
    """List storage pools."""
    pools = await storage_service.list_pools(host_id=host_id)
    
    members = []
    for pool in pools:
        capacity_gb = pool.capacity_bytes // (1024 * 1024 * 1024)
        allocated_gb = pool.allocated_bytes // (1024 * 1024 * 1024)
        available_gb = pool.available_bytes // (1024 * 1024 * 1024)
        
        members.append({
            "@odata.id": f"/redfish/v1/Oem/HawkFish/Storage/Pools/{pool.id}",
            "Id": pool.id,
            "Name": pool.name,
            "Type": pool.type,
            "TargetPath": pool.target_path,
            "CapacityGB": capacity_gb,
            "AllocatedGB": allocated_gb,
            "AvailableGB": available_gb,
            "State": pool.state,
            "Autostart": pool.autostart,
            "HostId": pool.host_id,
            "CreatedAt": pool.created_at,
            "Config": pool.config
        })
    
    return {
        "@odata.id": "/redfish/v1/Oem/HawkFish/Storage/Pools",
        "@odata.type": "#StoragePoolCollection.StoragePoolCollection",
        "Name": "Storage Pool Collection",
        "Members@odata.count": len(members),
        "Members": members
    }


@pools_router.post("")
async def create_pool(
    pool_data: PoolCreate,
    session=Depends(require_role("admin")),
):
    """Create a new storage pool."""
    try:
        config = pool_data.config.copy()
        config["capacity_gb"] = pool_data.capacity_gb
        
        pool = await storage_service.create_pool(
            name=pool_data.name,
            pool_type=pool_data.type,
            target_path=pool_data.target_path,
            host_id=pool_data.host_id,
            config=config,
            autostart=pool_data.autostart
        )
        
        capacity_gb = pool.capacity_bytes // (1024 * 1024 * 1024)
        
        return {
            "@odata.id": f"/redfish/v1/Oem/HawkFish/Storage/Pools/{pool.id}",
            "@odata.type": "#StoragePool.v1_0_0.StoragePool",
            "Id": pool.id,
            "Name": pool.name,
            "Type": pool.type,
            "TargetPath": pool.target_path,
            "CapacityGB": capacity_gb,
            "State": pool.state,
            "HostId": pool.host_id,
            "CreatedAt": pool.created_at
        }
        
    except Exception as e:
        return redfish_error("CreateFailed", str(e), 400)


@pools_router.get("/{pool_id}")
async def get_pool(
    pool_id: str,
    session=Depends(get_current_session),
):
    """Get storage pool details."""
    pool = await storage_service.get_pool(pool_id)
    if not pool:
        return redfish_error("ResourceNotFound", f"Pool {pool_id} not found", 404)
    
    capacity_gb = pool.capacity_bytes // (1024 * 1024 * 1024)
    allocated_gb = pool.allocated_bytes // (1024 * 1024 * 1024)
    available_gb = pool.available_bytes // (1024 * 1024 * 1024)
    
    return {
        "@odata.id": f"/redfish/v1/Oem/HawkFish/Storage/Pools/{pool.id}",
        "@odata.type": "#StoragePool.v1_0_0.StoragePool",
        "Id": pool.id,
        "Name": pool.name,
        "Type": pool.type,
        "TargetPath": pool.target_path,
        "CapacityGB": capacity_gb,
        "AllocatedGB": allocated_gb,
        "AvailableGB": available_gb,
        "State": pool.state,
        "Autostart": pool.autostart,
        "HostId": pool.host_id,
        "CreatedAt": pool.created_at,
        "Config": pool.config
    }


@pools_router.delete("/{pool_id}")
async def delete_pool(
    pool_id: str,
    session=Depends(require_role("admin")),
):
    """Delete a storage pool."""
    try:
        deleted = await storage_service.delete_pool(pool_id)
        if not deleted:
            return redfish_error("ResourceNotFound", f"Pool {pool_id} not found", 404)
        
        return {"status": "success", "message": f"Pool {pool_id} deleted"}
        
    except ValueError as e:
        return redfish_error("OperationFailed", str(e), 400)
    except Exception as e:
        return redfish_error("InternalError", str(e), 500)


# Storage Volumes endpoints
@volumes_router.get("")
async def list_volumes(
    pool_id: str = None,
    project_id: str = None,
    session=Depends(get_current_session),
):
    """List storage volumes."""
    # Filter by user's accessible projects if not admin
    if not session.get("is_admin") and not project_id:
        # In a full implementation, get user's accessible projects
        project_id = "default"
    
    volumes = await storage_service.list_volumes(pool_id=pool_id, project_id=project_id)
    
    members = []
    for volume in volumes:
        capacity_gb = volume.capacity_bytes // (1024 * 1024 * 1024)
        allocated_gb = volume.allocated_bytes // (1024 * 1024 * 1024)
        
        members.append({
            "@odata.id": f"/redfish/v1/Oem/HawkFish/Storage/Volumes/{volume.id}",
            "Id": volume.id,
            "Name": volume.name,
            "PoolId": volume.pool_id,
            "CapacityGB": capacity_gb,
            "AllocatedGB": allocated_gb,
            "Format": volume.format,
            "TargetPath": volume.target_path,
            "State": volume.state,
            "AttachedTo": volume.attached_to,
            "ProjectId": volume.project_id,
            "CreatedAt": volume.created_at,
            "Labels": volume.labels
        })
    
    return {
        "@odata.id": "/redfish/v1/Oem/HawkFish/Storage/Volumes",
        "@odata.type": "#StorageVolumeCollection.StorageVolumeCollection",
        "Name": "Storage Volume Collection",
        "Members@odata.count": len(members),
        "Members": members
    }


@volumes_router.post("")
async def create_volume(
    volume_data: VolumeCreate,
    session=Depends(get_current_session),
):
    """Create a new storage volume."""
    # Check project access
    user_id = session.get("user_id") if session else None
    if not user_id:
        return redfish_error("AuthenticationRequired", "Authentication required", 401)
    
    try:
        capacity_bytes = volume_data.capacity_gb * 1024 * 1024 * 1024
        
        volume = await storage_service.create_volume(
            name=volume_data.name,
            pool_id=volume_data.pool_id,
            capacity_bytes=capacity_bytes,
            format=volume_data.format,
            project_id=volume_data.project_id,
            labels=volume_data.labels
        )
        
        capacity_gb = volume.capacity_bytes // (1024 * 1024 * 1024)
        
        return {
            "@odata.id": f"/redfish/v1/Oem/HawkFish/Storage/Volumes/{volume.id}",
            "@odata.type": "#StorageVolume.v1_0_0.StorageVolume",
            "Id": volume.id,
            "Name": volume.name,
            "PoolId": volume.pool_id,
            "CapacityGB": capacity_gb,
            "Format": volume.format,
            "ProjectId": volume.project_id,
            "CreatedAt": volume.created_at
        }
        
    except Exception as e:
        return redfish_error("CreateFailed", str(e), 400)


@volumes_router.get("/{volume_id}")
async def get_volume(
    volume_id: str,
    session=Depends(get_current_session),
):
    """Get storage volume details."""
    volume = await storage_service.get_volume(volume_id)
    if not volume:
        return redfish_error("ResourceNotFound", f"Volume {volume_id} not found", 404)
    
    capacity_gb = volume.capacity_bytes // (1024 * 1024 * 1024)
    allocated_gb = volume.allocated_bytes // (1024 * 1024 * 1024)
    
    return {
        "@odata.id": f"/redfish/v1/Oem/HawkFish/Storage/Volumes/{volume.id}",
        "@odata.type": "#StorageVolume.v1_0_0.StorageVolume",
        "Id": volume.id,
        "Name": volume.name,
        "PoolId": volume.pool_id,
        "CapacityGB": capacity_gb,
        "AllocatedGB": allocated_gb,
        "Format": volume.format,
        "TargetPath": volume.target_path,
        "State": volume.state,
        "AttachedTo": volume.attached_to,
        "ProjectId": volume.project_id,
        "CreatedAt": volume.created_at,
        "Labels": volume.labels
    }


@volumes_router.delete("/{volume_id}")
async def delete_volume(
    volume_id: str,
    session=Depends(get_current_session),
):
    """Delete a storage volume."""
    # Check ownership/access
    volume = await storage_service.get_volume(volume_id)
    if not volume:
        return redfish_error("ResourceNotFound", f"Volume {volume_id} not found", 404)
    
    # Check project access (simplified for now)
    if not session.get("is_admin") and volume.project_id != "default":
        return redfish_error("AccessDenied", "Insufficient permissions", 403)
    
    try:
        deleted = await storage_service.delete_volume(volume_id)
        if not deleted:
            return redfish_error("ResourceNotFound", f"Volume {volume_id} not found", 404)
        
        return {"status": "success", "message": f"Volume {volume_id} deleted"}
        
    except ValueError as e:
        return redfish_error("OperationFailed", str(e), 400)
    except Exception as e:
        return redfish_error("InternalError", str(e), 500)


# System Volume Actions
@system_volumes_router.post("/{system_id}/Oem/HawkFish/Volumes/Attach")
async def attach_volume_to_system(
    system_id: str,
    attach_data: VolumeAttach,
    session=Depends(get_current_session),
):
    """Attach a volume to a system."""
    try:
        attached = await storage_service.attach_volume(
            volume_id=attach_data.volume_id,
            system_id=system_id,
            device=attach_data.device
        )
        
        if not attached:
            return redfish_error("OperationFailed", "Failed to attach volume", 500)
        
        # Emit event
        from ..services.events import publish_event, subscription_store
        await publish_event("VolumeAttached", {
            "systemId": system_id,
            "volumeId": attach_data.volume_id,
            "device": attach_data.device
        }, subscription_store)
        
        return {
            "@odata.type": "#ActionInfo.v1_0_0.ActionInfo",
            "Id": "VolumeAttach",
            "SystemId": system_id,
            "VolumeId": attach_data.volume_id,
            "Device": attach_data.device,
            "State": "Completed"
        }
        
    except Exception as e:
        return redfish_error("OperationFailed", str(e), 500)


@system_volumes_router.post("/{system_id}/Oem/HawkFish/Volumes/Detach")
async def detach_volume_from_system(
    system_id: str,
    detach_data: dict,  # {volume_id: str}
    session=Depends(get_current_session),
):
    """Detach a volume from a system."""
    volume_id = detach_data.get("volume_id")
    if not volume_id:
        return redfish_error("MissingParameter", "volume_id is required", 400)
    
    try:
        detached = await storage_service.detach_volume(volume_id)
        
        if not detached:
            return redfish_error("OperationFailed", "Failed to detach volume", 500)
        
        # Emit event
        from ..services.events import publish_event, subscription_store
        await publish_event("VolumeDetached", {
            "systemId": system_id,
            "volumeId": volume_id
        }, subscription_store)
        
        return {
            "@odata.type": "#ActionInfo.v1_0_0.ActionInfo",
            "Id": "VolumeDetach",
            "SystemId": system_id,
            "VolumeId": volume_id,
            "State": "Completed"
        }
        
    except Exception as e:
        return redfish_error("OperationFailed", str(e), 500)


@system_volumes_router.post("/{system_id}/Oem/HawkFish/Volumes/{volume_id}/Resize")
async def resize_volume_action(
    system_id: str,
    volume_id: str,
    resize_data: VolumeResize,
    session=Depends(get_current_session),
):
    """Resize a volume."""
    try:
        new_capacity_bytes = resize_data.capacity_gb * 1024 * 1024 * 1024
        
        resized = await storage_service.resize_volume(volume_id, new_capacity_bytes)
        
        if not resized:
            return redfish_error("OperationFailed", "Failed to resize volume", 500)
        
        # Emit event
        from ..services.events import publish_event, subscription_store
        await publish_event("VolumeResized", {
            "systemId": system_id,
            "volumeId": volume_id,
            "newCapacityGB": resize_data.capacity_gb
        }, subscription_store)
        
        return {
            "@odata.type": "#ActionInfo.v1_0_0.ActionInfo",
            "Id": "VolumeResize",
            "SystemId": system_id,
            "VolumeId": volume_id,
            "NewCapacityGB": resize_data.capacity_gb,
            "State": "Completed"
        }
        
    except Exception as e:
        return redfish_error("OperationFailed", str(e), 500)
