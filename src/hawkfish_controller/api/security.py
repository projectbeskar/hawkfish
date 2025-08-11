from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..services.security import set_user

router = APIRouter(prefix="/redfish/v1/Users", tags=["Security"])


@router.post("")
async def add_user(body: dict):
    username = body.get("UserName")
    password = body.get("Password")
    role = body.get("Role", "viewer")
    if not username or not password:
        raise HTTPException(status_code=400, detail="UserName and Password required")
    await set_user(username, password, role)
    return {"Id": username, "Role": role}


