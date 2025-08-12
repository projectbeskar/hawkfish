from fastapi import APIRouter, Depends, Query

from ..services.audit import audit_logger
from ..services.security import require_role

router = APIRouter(prefix="/redfish/v1/Oem/HawkFish/Audit", tags=["Audit"])


@router.get("/Logs")
async def get_audit_logs(
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of logs to return"),
    offset: int = Query(0, ge=0, description="Number of logs to skip"),
    user_id: str | None = Query(None, description="Filter by user ID"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    resource_id: str | None = Query(None, description="Filter by resource ID"),
    action: str | None = Query(None, description="Filter by action"),
    start_time: str | None = Query(None, description="Filter by start time (ISO format)"),
    end_time: str | None = Query(None, description="Filter by end time (ISO format)"),
    success: bool | None = Query(None, description="Filter by success status"),
    session=Depends(require_role("admin")),  # Only admins can view audit logs
):
    """Get audit logs with optional filtering."""
    result = await audit_logger.get_audit_logs(
        limit=limit,
        offset=offset,
        user_id=user_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        start_time=start_time,
        end_time=end_time,
        success=success,
    )
    
    # Format as Redfish collection
    members = []
    for i, log in enumerate(result["logs"]):
        log_id = f"log_{offset + i + 1}"
        members.append({
            "@odata.id": f"/redfish/v1/Oem/HawkFish/Audit/Logs/{log_id}",
            "Id": log_id,
            "Timestamp": log["timestamp"],
            "UserId": log["user_id"],
            "Action": log["action"],
            "ResourceType": log["resource_type"],
            "ResourceId": log["resource_id"],
            "Method": log["method"],
            "Path": log["path"],
            "StatusCode": log["status_code"],
            "Success": log["success"],
            "Duration": log["duration_ms"],
            "Details": log["details"],
        })
    
    return {
        "@odata.id": "/redfish/v1/Oem/HawkFish/Audit/Logs",
        "@odata.type": "#LogEntryCollection.LogEntryCollection",
        "Name": "Audit Log Collection",
        "Description": "Collection of audit log entries",
        "Members@odata.count": len(members),
        "Members": members,
        "Oem": {
            "HawkFish": {
                "TotalCount": result["total_count"],
                "HasMore": result["has_more"],
                "Limit": result["limit"],
                "Offset": result["offset"],
            }
        }
    }


@router.get("/Stats")
async def get_audit_stats(
    session=Depends(check_role("admin")),
):
    """Get audit log statistics."""
    stats = await audit_logger.get_audit_stats()
    
    return {
        "@odata.id": "/redfish/v1/Oem/HawkFish/Audit/Stats",
        "@odata.type": "#OemObject.v1_0_0.OemObject",
        "Name": "Audit Statistics",
        "Description": "Audit log statistics and metrics",
        "TotalEntries": stats["total_entries"],
        "SuccessfulOperations": stats["successful_operations"],
        "FailedOperations": stats["failed_operations"],
        "RecentActivity24h": stats["recent_activity_24h"],
        "TopActions": stats["top_actions"],
        "TopUsers": stats["top_users"],
    }
