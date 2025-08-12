from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from jsonschema import Draft7Validator, ValidationError

from ..services.profiles import create_profile, delete_profile, get_profile, list_profiles
from ..services.security import check_role
from .sessions import require_session

router = APIRouter(prefix="/redfish/v1/Oem/HawkFish/Profiles", tags=["Profiles"])


@router.get("")
async def profiles_list(page: int = 1, per_page: int = 50, session=Depends(require_session)):
    """List profiles with pagination."""
    profiles = await list_profiles()
    
    # Apply pagination
    total_count = len(profiles)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_profiles = profiles[start_idx:end_idx]
    
    # Build pagination links
    base_url = "/redfish/v1/Oem/HawkFish/Profiles"
    pagination = {}
    
    if page > 1:
        pagination["@odata.prevLink"] = f"{base_url}?page={page-1}&per_page={per_page}"
    
    if end_idx < total_count:
        pagination["@odata.nextLink"] = f"{base_url}?page={page+1}&per_page={per_page}"
    
    result = {
        "@odata.type": "#Collection.Collection",
        "@odata.id": base_url,
        "Name": "Profiles Collection",
        "Members@odata.count": len(paginated_profiles),
        "Members": [{"@odata.id": f"{base_url}/{p.id}", "Id": p.id} for p in paginated_profiles]
    }
    result.update(pagination)
    
    return result


@router.get("/{profile_id}")
async def profiles_get(profile_id: str, session=Depends(require_session)):
    p = await get_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Not found")
    return {"Id": p.id, "Spec": p.spec}


PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "Name": {"type": "string"},
        "CPU": {"type": "integer", "minimum": 1},
        "MemoryMiB": {"type": "integer", "minimum": 128},
        "DiskGiB": {"type": "integer", "minimum": 1},
        "Network": {"type": "string"},
        "Boot": {"type": "object", "properties": {"Primary": {"enum": ["Hdd", "Cd", "Pxe", "Usb"]}}},
        "Image": {"type": "object", "properties": {"type": {"type": "string"}, "url": {"type": "string"}}},
        "CloudInit": {"type": "object"},
    },
    "required": ["Name"],
}


@router.post("")
async def profiles_create(body: dict, session=Depends(require_session)):
    if not check_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    profile_id = body.get("Name")
    if not profile_id:
        raise HTTPException(status_code=400, detail="Name required")
    try:
        Draft7Validator(PROFILE_SCHEMA).validate(body)
    except ValidationError as exc:  # pragma: no cover - schema
        raise HTTPException(status_code=400, detail=f"Invalid profile: {exc.message}") from exc
    p = await create_profile(profile_id, body)
    return {"Id": p.id}


@router.delete("/{profile_id}")
async def profiles_delete(profile_id: str, session=Depends(require_session)):
    if not check_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    await delete_profile(profile_id)
    return {"TaskState": "Completed"}


