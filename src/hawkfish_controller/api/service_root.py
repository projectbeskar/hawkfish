from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from ..services.libvirt_pool import pool_manager

router = APIRouter(prefix="/redfish/v1", tags=["ServiceRoot"])


@router.get("/")
def get_service_root():
    return {
        "@odata.type": "#ServiceRoot.v1_11_0.ServiceRoot",
        "@odata.id": "/redfish/v1/",
        "Id": "RootService",
        "Name": "HawkFish Redfish Service",
        "RedfishVersion": "1.18.0",
        "Systems": {"@odata.id": "/redfish/v1/Systems"},
        "Managers": {"@odata.id": "/redfish/v1/Managers"},
        "Chassis": {"@odata.id": "/redfish/v1/Chassis"},
        "SessionService": {"@odata.id": "/redfish/v1/SessionService"},
        "TaskService": {"@odata.id": "/redfish/v1/TaskService"},
        "EventService": {"@odata.id": "/redfish/v1/EventService"},
        "UpdateService": {"@odata.id": "/redfish/v1/UpdateService"},
        "Links": {
            "Sessions": {"@odata.id": "/redfish/v1/SessionService/Sessions"}
        },
        "Oem": {
            "HawkFish": {
                "Profiles": {"@odata.id": "/redfish/v1/Oem/HawkFish/Profiles"},
                "Hosts": {"@odata.id": "/redfish/v1/Oem/HawkFish/Hosts"},
                "Images": {"@odata.id": "/redfish/v1/Oem/HawkFish/Images"},
                "NetworkProfiles": {"@odata.id": "/redfish/v1/Oem/HawkFish/NetworkProfiles"}
            }
        }
    }


@router.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/libvirt-pool-metrics")
def libvirt_pool_metrics():
    """Get libvirt connection pool metrics."""
    return pool_manager.get_metrics()


