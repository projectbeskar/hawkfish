from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..services.projects import project_store
from ..services.security import check_role, get_current_session
from .errors import redfish_error

router = APIRouter(prefix="/redfish/v1/Oem/HawkFish/Projects", tags=["Projects"])


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    labels: dict[str, str] = {}
    quotas: dict[str, int] = {
        "vcpus": 100,
        "memory_gib": 500,
        "disk_gib": 1000,
        "systems": 50
    }


class ProjectMemberAdd(BaseModel):
    user_id: str
    role: str  # admin, operator, viewer


class QuotaUpdate(BaseModel):
    quotas: dict[str, int]


@router.get("")
async def list_projects(
    session=Depends(get_current_session),
):
    """List projects accessible to the current user."""
    user_id = session.get("user_id") if session else None
    projects = await project_store.list_projects(user_id=user_id)
    
    members = []
    for project in projects:
        members.append({
            "@odata.id": f"/redfish/v1/Oem/HawkFish/Projects/{project.id}",
            "Id": project.id,
            "Name": project.name,
            "Description": project.description,
            "Labels": project.labels,
            "Quotas": project.quotas,
            "Usage": project.usage,
            "CreatedAt": project.created_at
        })
    
    return {
        "@odata.id": "/redfish/v1/Oem/HawkFish/Projects",
        "@odata.type": "#ProjectCollection.ProjectCollection",
        "Name": "Project Collection",
        "Description": "Collection of multi-tenant projects",
        "Members@odata.count": len(members),
        "Members": members
    }


@router.post("")
async def create_project(
    project_data: ProjectCreate,
    session=Depends(check_role("admin")),  # Only admins can create projects
):
    """Create a new project."""
    try:
        # Generate project ID from name
        project_id = project_data.name.lower().replace(" ", "-").replace("_", "-")
        
        project = await project_store.create_project(
            project_id=project_id,
            name=project_data.name,
            description=project_data.description,
            labels=project_data.labels,
            quotas=project_data.quotas
        )
        
        return {
            "@odata.id": f"/redfish/v1/Oem/HawkFish/Projects/{project.id}",
            "@odata.type": "#Project.v1_0_0.Project",
            "Id": project.id,
            "Name": project.name,
            "Description": project.description,
            "Labels": project.labels,
            "Quotas": project.quotas,
            "Usage": project.usage,
            "CreatedAt": project.created_at
        }
    
    except Exception as e:
        return redfish_error("CreateFailed", str(e), 400)


@router.get("/{project_id}")
async def get_project(
    project_id: str,
    session=Depends(get_current_session),
):
    """Get project details."""
    # Check if user has access to this project
    if session:
        user_id = session.get("user_id")
        if user_id and project_id != "default":
            role = await project_store.get_user_role(project_id, user_id)
            if not role and not session.get("is_admin"):
                return redfish_error("AccessDenied", "No access to this project", 403)
    
    project = await project_store.get_project(project_id)
    if not project:
        return redfish_error("ResourceNotFound", f"Project {project_id} not found", 404)
    
    return {
        "@odata.id": f"/redfish/v1/Oem/HawkFish/Projects/{project.id}",
        "@odata.type": "#Project.v1_0_0.Project",
        "Id": project.id,
        "Name": project.name,
        "Description": project.description,
        "Labels": project.labels,
        "Quotas": project.quotas,
        "Usage": project.usage,
        "CreatedAt": project.created_at
    }


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    session=Depends(check_role("admin")),
):
    """Delete a project."""
    try:
        deleted = await project_store.delete_project(project_id)
        if not deleted:
            return redfish_error("ResourceNotFound", f"Project {project_id} not found", 404)
        
        return {"status": "success", "message": f"Project {project_id} deleted"}
    
    except ValueError as e:
        return redfish_error("OperationFailed", str(e), 400)
    except Exception as e:
        return redfish_error("InternalError", str(e), 500)


@router.get("/{project_id}/Members")
async def list_project_members(
    project_id: str,
    session=Depends(get_current_session),
):
    """List project members."""
    # Check access
    if session:
        user_id = session.get("user_id")
        if user_id and project_id != "default":
            role = await project_store.get_user_role(project_id, user_id)
            if not role and not session.get("is_admin"):
                return redfish_error("AccessDenied", "No access to this project", 403)
    
    members = await project_store.list_members(project_id)
    
    member_list = []
    for member in members:
        member_list.append({
            "@odata.id": f"/redfish/v1/Oem/HawkFish/Projects/{project_id}/Members/{member.user_id}",
            "UserId": member.user_id,
            "Role": member.role,
            "AssignedAt": member.assigned_at,
            "AssignedBy": member.assigned_by
        })
    
    return {
        "@odata.id": f"/redfish/v1/Oem/HawkFish/Projects/{project_id}/Members",
        "@odata.type": "#ProjectMemberCollection.ProjectMemberCollection",
        "Name": "Project Members",
        "Members@odata.count": len(member_list),
        "Members": member_list
    }


@router.post("/{project_id}/Members")
async def add_project_member(
    project_id: str,
    member_data: ProjectMemberAdd,
    session=Depends(get_current_session),
):
    """Add a member to a project."""
    # Check if user has admin role in project or is global admin
    if session:
        user_id = session.get("user_id")
        if user_id:
            role = await project_store.get_user_role(project_id, user_id)
            if role != "admin" and not session.get("is_admin"):
                return redfish_error("AccessDenied", "Only project admins can add members", 403)
        assigned_by = user_id or "system"
    else:
        return redfish_error("AuthenticationRequired", "Authentication required", 401)
    
    if member_data.role not in ["admin", "operator", "viewer"]:
        return redfish_error("InvalidRole", f"Invalid role: {member_data.role}", 400)
    
    try:
        member = await project_store.add_member(
            project_id=project_id,
            user_id=member_data.user_id,
            role=member_data.role,
            assigned_by=assigned_by
        )
        
        return {
            "@odata.id": f"/redfish/v1/Oem/HawkFish/Projects/{project_id}/Members/{member.user_id}",
            "UserId": member.user_id,
            "Role": member.role,
            "AssignedAt": member.assigned_at,
            "AssignedBy": member.assigned_by
        }
    
    except Exception as e:
        return redfish_error("OperationFailed", str(e), 500)


@router.delete("/{project_id}/Members/{user_id}")
async def remove_project_member(
    project_id: str,
    user_id: str,
    session=Depends(get_current_session),
):
    """Remove a member from a project."""
    # Check access
    if session:
        current_user = session.get("user_id")
        if current_user:
            role = await project_store.get_user_role(project_id, current_user)
            if role != "admin" and not session.get("is_admin"):
                return redfish_error("AccessDenied", "Only project admins can remove members", 403)
    else:
        return redfish_error("AuthenticationRequired", "Authentication required", 401)
    
    removed = await project_store.remove_member(project_id, user_id)
    if not removed:
        return redfish_error("ResourceNotFound", f"User {user_id} not found in project", 404)
    
    return {"status": "success", "message": f"User {user_id} removed from project"}


@router.get("/{project_id}/Usage")
async def get_project_usage(
    project_id: str,
    session=Depends(get_current_session),
):
    """Get current resource usage for a project."""
    # Check access
    if session:
        user_id = session.get("user_id")
        if user_id and project_id != "default":
            role = await project_store.get_user_role(project_id, user_id)
            if not role and not session.get("is_admin"):
                return redfish_error("AccessDenied", "No access to this project", 403)
    
    project = await project_store.get_project(project_id)
    if not project:
        return redfish_error("ResourceNotFound", f"Project {project_id} not found", 404)
    
    # Calculate usage percentages
    usage_details = {}
    for resource_type, current_usage in project.usage.items():
        quota_limit = project.quotas.get(resource_type, 0)
        percentage = (current_usage / quota_limit * 100) if quota_limit > 0 else 0
        
        usage_details[resource_type] = {
            "current": current_usage,
            "quota": quota_limit,
            "available": max(0, quota_limit - current_usage),
            "percentage": round(percentage, 1)
        }
    
    return {
        "@odata.id": f"/redfish/v1/Oem/HawkFish/Projects/{project_id}/Usage",
        "@odata.type": "#ProjectUsage.v1_0_0.ProjectUsage",
        "ProjectId": project_id,
        "ProjectName": project.name,
        "Usage": usage_details,
        "LastUpdated": project.created_at  # Would be updated when usage changes
    }


@router.post("/{project_id}/Actions/SetQuotas")
async def set_project_quotas(
    project_id: str,
    quota_data: QuotaUpdate,
    session=Depends(check_role("admin")),
):
    """Set project quotas (admin only)."""
    user_id = session.get("user_id", "admin")
    
    try:
        await project_store.set_quotas(
            project_id=project_id,
            quotas=quota_data.quotas,
            updated_by=user_id
        )
        
        return {
            "status": "success",
            "message": f"Quotas updated for project {project_id}",
            "quotas": quota_data.quotas
        }
    
    except Exception as e:
        return redfish_error("OperationFailed", str(e), 500)
