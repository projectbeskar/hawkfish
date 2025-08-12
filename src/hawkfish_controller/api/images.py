from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from jsonschema import Draft7Validator, ValidationError

from ..services.images import add_image, delete_image, get_image, list_images, prune_unused_images
from ..services.security import check_role
from .sessions import require_session

router = APIRouter(prefix="/redfish/v1/Oem/HawkFish/Images", tags=["Images"])

IMAGE_SCHEMA = {
    "type": "object",
    "properties": {
        "Name": {"type": "string"},
        "Version": {"type": "string"},
        "URL": {"type": "string"},
        "SHA256": {"type": "string", "pattern": "^[a-fA-F0-9]{64}$"},
        "Labels": {"type": "object"},
    },
    "required": ["Name", "Version"],
}


@router.get("")
async def images_list(session=Depends(require_session)):
    """List all images in the catalog."""
    images = await list_images()
    return {
        "Members": [
            {
                "Id": img.id,
                "Name": img.name,
                "Version": img.version,
                "URL": img.url,
                "SHA256": img.sha256,
                "Size": img.size,
                "LocalPath": img.local_path,
                "CreatedAt": img.created_at,
                "LastUsedAt": img.last_used_at,
                "Labels": img.labels,
            }
            for img in images
        ]
    }


@router.get("/{image_id}")
async def images_get(image_id: str, session=Depends(require_session)):
    """Get details for a specific image."""
    image = await get_image(image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    return {
        "Id": image.id,
        "Name": image.name,
        "Version": image.version,
        "URL": image.url,
        "SHA256": image.sha256,
        "Size": image.size,
        "LocalPath": image.local_path,
        "CreatedAt": image.created_at,
        "LastUsedAt": image.last_used_at,
        "Labels": image.labels,
    }


@router.post("")
async def images_create(body: dict, session=Depends(require_session)):
    """Add a new image to the catalog."""
    if not check_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        Draft7Validator(IMAGE_SCHEMA).validate(body)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc.message}") from exc
    
    name = body["Name"]
    version = body["Version"]
    url = body.get("URL")
    sha256 = body.get("SHA256")
    labels = body.get("Labels", {})
    
    try:
        image = await add_image(name, version, url, sha256, labels)
        return {"Id": image.id, "Name": image.name, "Version": image.version}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to add image: {exc}") from exc


@router.delete("/{image_id}")
async def images_delete(image_id: str, session=Depends(require_session)):
    """Remove an image from the catalog."""
    if not check_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    await delete_image(image_id)
    return {"TaskState": "Completed"}


@router.post("/Actions/Prune")
async def images_prune(session=Depends(require_session)):
    """Remove unreferenced images."""
    if not check_role("admin", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    pruned = await prune_unused_images()
    return {"PrunedImages": pruned, "TaskState": "Completed"}
