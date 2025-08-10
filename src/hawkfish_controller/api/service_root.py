from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(prefix="/redfish/v1", tags=["ServiceRoot"])


@router.get("/")
def get_service_root():
    return {
        "@odata.type": "#ServiceRoot.v1_11_0.ServiceRoot",
        "@odata.id": "/redfish/v1/",
        "Id": "RootService",
        "Name": "HawkFish Redfish Service",
        "Links": {
            "Managers": {"@odata.id": "/redfish/v1/Managers"},
            "Chassis": {"@odata.id": "/redfish/v1/Chassis"},
            "Systems": {"@odata.id": "/redfish/v1/Systems"},
        },
        "RedfishVersion": "1.18.0",
        "Links": {
            "Systems": {"@odata.id": "/redfish/v1/Systems"},
            "Managers": {"@odata.id": "/redfish/v1/Managers"},
            "Chassis": {"@odata.id": "/redfish/v1/Chassis"},
        },
        "SessionService": {"@odata.id": "/redfish/v1/SessionService"},
        "TaskService": {"@odata.id": "/redfish/v1/TaskService"},
        "EventService": {"@odata.id": "/redfish/v1/EventService"},
        "Managers": {"@odata.id": "/redfish/v1/Managers"},
    }


@router.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


