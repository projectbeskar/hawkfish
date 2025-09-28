"""
Persona management API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..persona.registry import persona_registry
from ..services.persona import persona_service
from ..services.security import check_role, require_role
from .sessions import require_session

router = APIRouter(prefix="/redfish/v1/Oem/HawkFish/Personas", tags=["Personas"])


class PersonaAssignment(BaseModel):
    """Model for persona assignment requests."""
    persona: str


@router.get("")
async def list_available_personas(session=Depends(require_session)):
    """List all available personas."""
    return {
        "@odata.type": "#PersonaCollection.PersonaCollection", 
        "@odata.id": "/redfish/v1/Oem/HawkFish/Personas",
        "Name": "Available Personas",
        "Members": [
            {
                "@odata.id": f"/redfish/v1/Oem/HawkFish/Personas/{name}",
                "Name": name
            }
            for name in ["generic"] + persona_registry.list_personas()
        ],
        "Members@odata.count": len(persona_registry.list_personas()) + 1
    }


@router.get("/{persona_name}")
async def get_persona_info(persona_name: str, session=Depends(require_session)):
    """Get information about a specific persona."""
    if persona_name == "generic":
        return {
            "@odata.id": f"/redfish/v1/Oem/HawkFish/Personas/{persona_name}",
            "Id": persona_name,
            "Name": "Generic Redfish",
            "Description": "Standard Redfish implementation without vendor-specific extensions"
        }
    
    plugin = persona_registry.get_plugin(persona_name)
    if not plugin:
        raise HTTPException(status_code=404, detail=f"Persona {persona_name} not found")
    
    return {
        "@odata.id": f"/redfish/v1/Oem/HawkFish/Personas/{persona_name}",
        "Id": persona_name,
        "Name": plugin.name,
        "Description": f"Compatibility mode for {plugin.name}"
    }


@router.get("/Systems/{system_id}")
async def get_system_persona(system_id: str, session=Depends(require_session)):
    """Get the current persona for a system."""
    # For now, use default project
    persona = await persona_service.get_system_persona(system_id, "default")
    
    return {
        "@odata.id": f"/redfish/v1/Oem/HawkFish/Personas/Systems/{system_id}",
        "SystemId": system_id,
        "Persona": persona,
        "Source": "project_default" if persona == await persona_service.get_project_default_persona("default") else "system_override"
    }


@router.patch("/Systems/{system_id}")
async def set_system_persona(
    system_id: str, 
    assignment: PersonaAssignment,
    session=Depends(require_session)
):
    """Set persona for a specific system (admin only)."""
    if not check_role("admin", session.role):
        raise HTTPException(status_code=403, detail="Only project admins can change system personas")
    
    try:
        await persona_service.set_system_persona(system_id, assignment.persona, session.username)
        return {
            "TaskState": "Completed",
            "Message": f"System {system_id} persona set to {assignment.persona}"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/Systems/{system_id}")
async def remove_system_persona(system_id: str, session=Depends(require_session)):
    """Remove system persona override (fall back to project default)."""
    if not check_role("admin", session.role):
        raise HTTPException(status_code=403, detail="Only project admins can change system personas")
    
    await persona_service.remove_system_persona(system_id)
    return {
        "TaskState": "Completed",
        "Message": f"System {system_id} persona override removed"
    }
