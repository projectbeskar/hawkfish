from __future__ import annotations

from typing import Any, Callable

from fastapi import Depends, HTTPException

from .projects import project_store
from ..api.sessions import require_session


def get_current_session():
    """Get the current session (dependency that doesn't raise errors)."""
    try:
        return require_session()
    except HTTPException:
        return None


def require_role(required_role: str) -> Callable:
    """Dependency that requires a specific global role."""
    def dependency(session=Depends(require_session)):
        if not session:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        user_role = session.get("role", "viewer")
        if required_role == "admin" and user_role != "admin":
            raise HTTPException(status_code=403, detail="Admin role required")
        
        return session
    
    return dependency


def check_role(required_role: str, user_role: str) -> bool:
    """Simple role check function."""
    role_hierarchy = {"viewer": 1, "operator": 2, "admin": 3}
    required_level = role_hierarchy.get(required_role, 3)
    user_level = role_hierarchy.get(user_role, 0)
    return user_level >= required_level


def require_project_role(project_id: str, required_role: str) -> Callable:
    """Dependency that requires a specific role in a project."""
    async def dependency(session=Depends(require_session)):
        if not session:
            raise HTTPException(status_code=401, detail="Authentication required")
        
        user_id = session.username
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid session")
        
        # Global admins have access to all projects
        if session.role == "admin":
            return session
        
        # Check project-specific role
        user_role = await project_store.get_user_role(project_id, user_id)
        if not user_role:
            raise HTTPException(status_code=403, detail="No access to this project")
        
        # Check if user has sufficient role
        role_hierarchy = {"viewer": 1, "operator": 2, "admin": 3}
        required_level = role_hierarchy.get(required_role, 3)
        user_level = role_hierarchy.get(user_role, 0)
        
        if user_level < required_level:
            raise HTTPException(
                status_code=403,
                detail=f"Project {required_role} role required, but user has {user_role}"
            )
        
        return session
    
    return dependency


async def filter_projects_by_access(projects: list[dict[str, Any]], session: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Filter a list of projects based on user access."""
    if not session:
        return []
    
    user_id = session.username
    if not user_id:
        return []
    
    # Global admins see all projects  
    if session.role == "admin":
        return projects
    
    # Filter to projects where user has a role
    accessible_projects = []
    for project in projects:
        project_id = project.get("Id") or project.get("id")
        if project_id == "default":
            # Everyone has access to default project
            accessible_projects.append(project)
        else:
            role = await project_store.get_user_role(project_id, user_id)
            if role:
                accessible_projects.append(project)
    
    return accessible_projects


async def check_project_access(project_id: str, session: dict[str, Any] | None, required_role: str = "viewer") -> bool:
    """Check if user has access to a project with the required role."""
    if not session:
        return False
    
    user_id = session.username
    if not user_id:
        return False
    
    # Global admins have access to all projects
    if session.role == "admin":
        return True
    
    # Default project is accessible to all authenticated users
    if project_id == "default":
        return True
    
    # Check project-specific role
    user_role = await project_store.get_user_role(project_id, user_id)
    if not user_role:
        return False
    
    # Check if user has sufficient role
    role_hierarchy = {"viewer": 1, "operator": 2, "admin": 3}
    required_level = role_hierarchy.get(required_role, 3)
    user_level = role_hierarchy.get(user_role, 0)
    
    return user_level >= required_level