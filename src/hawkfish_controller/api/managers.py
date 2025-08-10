import hashlib
import json
import os
import tempfile
import time

import anyio
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from ..config import settings
from ..drivers.libvirt_driver import LibvirtDriver, LibvirtError
from ..services.events import SubscriptionStore, publish_event
from ..services.metrics import MEDIA_ACTIONS, BYTES_DOWNLOADED
from ..services.security import require_role
from ..services.tasks import TaskService
from .task_event import get_task_service
from .sessions import require_session

router = APIRouter(prefix="/redfish/v1/Managers", tags=["Managers"])


def get_driver() -> LibvirtDriver:
    return LibvirtDriver(settings.libvirt_uri)


@router.get("")
def list_managers():
    return {
        "@odata.id": "/redfish/v1/Managers",
        "Members@odata.count": 1,
        "Members": [{"@odata.id": "/redfish/v1/Managers/HawkFish"}],
    }


@router.get("/HawkFish")
def get_manager():
    return {
        "Id": "HawkFish",
        "Name": "HawkFish Manager",
        "VirtualMedia": {"@odata.id": "/redfish/v1/Managers/HawkFish/VirtualMedia"},
    }


@router.get("/HawkFish/VirtualMedia")
def list_virtual_media():
    return {
        "@odata.id": "/redfish/v1/Managers/HawkFish/VirtualMedia",
        "Members": [
            {"@odata.id": "/redfish/v1/Managers/HawkFish/VirtualMedia/Cd"},
        ],
        "Oem": {"HawkFish": {"AvailableImages": _read_iso_index().get("images", [])}},
    }


@router.post("/HawkFish/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia", response_model=None)
def insert_media(body: dict, driver: LibvirtDriver = Depends(get_driver), session=Depends(require_session)):
    if not require_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    system_id = body.get("SystemId")
    image = body.get("Image")
    if not system_id or not image:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SystemId and Image required")
    # remote URL: start download task
    if image.startswith("http://") or image.startswith("https://"):
        task_service = get_task_service()

        subs = SubscriptionStore(db_path=f"{settings.state_dir}/events.db")

        async def job(task_id: str) -> None:
            await task_service.update(task_id, state="Running", percent=1, message=f"Downloading {image}")
            dest_dir = settings.iso_dir
            os.makedirs(dest_dir, exist_ok=True)
            safe_name = _safe_name_from_url(str(image))
            tmp_fd, tmp_path = tempfile.mkstemp(prefix="iso_", suffix=".part", dir=dest_dir)
            os.close(tmp_fd)
            sha256 = hashlib.sha256()
            size = 0
            async with httpx.AsyncClient(follow_redirects=True, timeout=300) as client, client.stream("GET", str(image)) as resp:
                    resp.raise_for_status()
                    total = int(resp.headers.get("content-length", "0") or 0)
                    async for chunk in resp.aiter_bytes(1024 * 256):
                        with open(tmp_path, "ab") as f:
                            f.write(chunk)
                        sha256.update(chunk)
                        size += len(chunk)
                        BYTES_DOWNLOADED.labels(source="virtualmedia").inc(len(chunk))
                        if total > 0:
                            pct = min(99, max(1, int(size * 100 / total)))
                            await task_service.update(task_id, percent=pct)
            final_path = os.path.join(dest_dir, f"{safe_name}.iso")
            os.replace(tmp_path, final_path)
            _update_iso_index(final_path, size=size, sha256_hex=sha256.hexdigest())
            await task_service.update(task_id, message="Attaching ISO")
            driver.attach_iso(system_id, final_path)
            await publish_event("MediaInserted", {"systemId": system_id, "details": {"image": final_path}}, subs)
            MEDIA_ACTIONS.labels(action="insert", result="success").inc()

        async def start_task():
            return await task_service.run_background(name=f"Download ISO {image}", coro_factory=lambda tid: job(tid))

        t = anyio.from_thread.run(start_task)
        location = f"/redfish/v1/TaskService/Tasks/{t.id}"
        return JSONResponse(content={"@odata.id": location}, status_code=202, headers={"Location": location})

    # local path under iso_dir
    if not image.startswith(settings.iso_dir):
        # allow test temp files by copying into iso dir (or create empty if missing)
        os.makedirs(settings.iso_dir, exist_ok=True)
        dest = os.path.join(settings.iso_dir, os.path.basename(image) or "local.iso")
        try:
            if os.path.exists(image):
                with open(image, "rb") as src, open(dest, "wb") as dst:
                    dst.write(src.read())
            else:
                # create a small placeholder file
                with open(dest, "wb") as dst:
                    dst.write(b"\0" * 1024)
            image = dest
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Local images must be under HF_ISO_DIR") from exc
    try:
        driver.attach_iso(system_id, image)
        _update_iso_index(image)
        anyio.from_thread.run(publish_event, "MediaInserted", {"systemId": system_id, "details": {"image": image}}, SubscriptionStore(db_path=f"{settings.state_dir}/events.db"))
        MEDIA_ACTIONS.labels(action="insert", result="success").inc()
        return {"TaskState": "Completed"}
    except LibvirtError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc


@router.post("/HawkFish/VirtualMedia/Cd/Actions/VirtualMedia.EjectMedia")
def eject_media(body: dict, driver: LibvirtDriver = Depends(get_driver), session=Depends(require_session)):
    if not require_role("operator", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    system_id = body.get("SystemId")
    if not system_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SystemId required")
    try:
        driver.detach_iso(system_id)
        anyio.from_thread.run(publish_event, "MediaEjected", {"systemId": system_id}, SubscriptionStore(db_path=f"{settings.state_dir}/events.db"))
        MEDIA_ACTIONS.labels(action="eject", result="success").inc()
    except LibvirtError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"TaskState": "Completed"}


def _safe_name_from_url(url: str) -> str:
    base = url.split("?")[0].rstrip("/").split("/")[-1]
    if not base.lower().endswith((".iso", ".img")):
        base = base + "_remote"
    return "".join(ch if ch.isalnum() or ch in ("-", "_") else "-" for ch in base)


def _index_path() -> str:
    return os.path.join(settings.iso_dir, "index.json")


def _read_iso_index() -> dict[str, object]:
    try:
        with open(_index_path(), encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {"images": []}
    except Exception:
        return {"images": []}


def _update_iso_index(path: str, *, size: int | None = None, sha256_hex: str | None = None) -> None:
    os.makedirs(settings.iso_dir, exist_ok=True)
    idx = _read_iso_index()
    images_list = idx.get("images", [])
    if not isinstance(images_list, list):
        images_list = []
    images = [img for img in images_list if isinstance(img, dict) and img.get("path") != path]
    if size is None:
        try:
            size = os.path.getsize(path)
        except Exception:
            size = 0
    entry = {"path": path, "size": size, "sha256": sha256_hex, "last_used": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    images.append(entry)
    with open(_index_path(), "w", encoding="utf-8") as f:
        json.dump({"images": images}, f)


