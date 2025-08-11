from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from ..config import settings

router = APIRouter(prefix="/oem/hawkfish", tags=["PXE"])


@router.get("/boot/{system_id}/ipxe")
def ipxe_script(system_id: str):
    script = "#!ipxe\n\nchain --autofree https://boot.netboot.xyz\n"
    return PlainTextResponse(script, media_type="text/plain")


@router.get("/httpboot/{path:path}")
def httpboot(path: str):
    base = os.path.join(settings.state_dir, "httpboot")
    full = os.path.realpath(os.path.join(base, path))
    if not full.startswith(os.path.realpath(base)):
        raise HTTPException(status_code=403, detail="Forbidden")
    if not os.path.exists(full):
        raise HTTPException(status_code=404, detail="Not found")
    return FileResponse(full)


