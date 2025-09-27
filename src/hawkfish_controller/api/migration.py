"""
Migration API endpoints for live migration operations.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..services.hosts import get_host
from ..services.migration import migration_service
from ..services.security import check_role
from .sessions import require_session

router = APIRouter(prefix="/redfish/v1/Oem/HawkFish/Migration", tags=["Migration"])


class MigrateSystemRequest(BaseModel):
    """Request model for system migration."""
    target_host_id: str
    live: bool = True
    copy_storage: bool | None = None
    max_downtime_ms: int = 300
    bandwidth_mbps: int = 100
    auto_converge: bool = True


@router.post("/Systems/{system_id}/Actions/Migrate")
async def migrate_system(
    system_id: str,
    request: MigrateSystemRequest,
    session=Depends(require_session)
):
    """Migrate a system to another host."""
    if not check_role("admin", session.role):
        raise HTTPException(status_code=403, detail="Admin role required for migration")
    
    try:
        # Import here to avoid circular imports
        from ..services.hosts import get_systems_on_host, migrate_system as hosts_migrate
        
        # For now, delegate to the hosts service migrate function
        # This maintains backward compatibility while we transition
        task_id = await hosts_migrate(
            system_id=system_id,
            source_host_id="default",  # TODO: Get actual source host from system
            target_host_id=request.target_host_id,
            live=request.live
        )
        
        return {
            "TaskId": task_id,
            "TaskState": "Running",
            "Message": "Migration started",
            "@Message.ExtendedInfo": [{
                "MessageId": "Migration.Started",
                "Message": f"Live migration of system {system_id} to host {request.target_host_id} has started",
                "Severity": "OK"
            }]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Migration failed: {str(e)}"
        )


@router.get("/Systems/{system_id}/History")
async def get_migration_history(
    system_id: str,
    session=Depends(require_session)
):
    """Get migration history for a system."""
    try:
        migrations = await migration_service.list_migrations(system_id=system_id)
        
        return {
            "@odata.type": "#MigrationHistoryCollection.MigrationHistoryCollection",
            "@odata.id": f"/redfish/v1/Oem/HawkFish/Migration/Systems/{system_id}/History",
            "Name": "Migration History",
            "Members": [
                {
                    "@odata.id": f"/redfish/v1/Oem/HawkFish/Migration/History/{migration['id']}",
                    "Id": migration["id"],
                    "SystemId": migration["system_id"],
                    "SourceHost": migration["source_host_id"],
                    "TargetHost": migration["target_host_id"],
                    "Status": migration["status"],
                    "StartedAt": migration["started_at"],
                    "CompletedAt": migration["completed_at"],
                    "DowntimeMs": migration["downtime_ms"]
                }
                for migration in migrations
            ],
            "Members@odata.count": len(migrations)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get migration history: {str(e)}"
        )


@router.get("/History/{migration_id}")
async def get_migration_details(
    migration_id: str,
    session=Depends(require_session)
):
    """Get detailed information about a specific migration."""
    try:
        migration = await migration_service.get_migration_status(migration_id)
        
        if not migration:
            raise HTTPException(status_code=404, detail="Migration not found")
        
        return {
            "@odata.type": "#Migration.v1_0_0.Migration",
            "@odata.id": f"/redfish/v1/Oem/HawkFish/Migration/History/{migration_id}",
            "Id": migration_id,
            "Name": f"Migration {migration_id}",
            "SystemId": migration["system_id"],
            "SourceHost": migration["source_host_id"],
            "TargetHost": migration["target_host_id"],
            "MigrationType": migration["migration_type"],
            "Status": migration["status"],
            "StartedAt": migration["started_at"],
            "CompletedAt": migration["completed_at"],
            "DowntimeMs": migration["downtime_ms"],
            "ErrorMessage": migration["error_message"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get migration details: {str(e)}"
        )
