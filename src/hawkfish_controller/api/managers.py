from fastapi import APIRouter, Depends, HTTPException, status

from ..config import settings
from ..drivers.libvirt_driver import LibvirtDriver, LibvirtError

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
    }


@router.post("/HawkFish/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia")
def insert_media(body: dict, driver: LibvirtDriver = Depends(get_driver)):
    system_id = body.get("SystemId")
    image = body.get("Image")
    if not system_id or not image:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SystemId and Image required")
    try:
        driver.attach_iso(system_id, image)
    except LibvirtError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"TaskState": "Completed"}


@router.post("/HawkFish/VirtualMedia/Cd/Actions/VirtualMedia.EjectMedia")
def eject_media(body: dict, driver: LibvirtDriver = Depends(get_driver)):
    system_id = body.get("SystemId")
    if not system_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SystemId required")
    try:
        driver.detach_iso(system_id)
    except LibvirtError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return {"TaskState": "Completed"}


