from fastapi import APIRouter

router = APIRouter(prefix="/redfish/v1", tags=["ServiceRoot"])


@router.get("/")
def get_service_root():
    return {
        "@odata.type": "#ServiceRoot.v1_11_0.ServiceRoot",
        "@odata.id": "/redfish/v1/",
        "Id": "RootService",
        "Name": "HawkFish Redfish Service",
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


