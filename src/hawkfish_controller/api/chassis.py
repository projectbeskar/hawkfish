from fastapi import APIRouter

router = APIRouter(prefix="/redfish/v1/Chassis", tags=["Chassis"])


@router.get("")
def list_chassis():
    return {
        "@odata.id": "/redfish/v1/Chassis",
        "Members": [{"@odata.id": "/redfish/v1/Chassis/HawkFishChassis"}],
    }


@router.get("/HawkFishChassis")
def get_chassis():
    return {
        "@odata.id": "/redfish/v1/Chassis/HawkFishChassis",
        "Id": "HawkFishChassis",
        "Name": "HawkFish Chassis",
        "Links": {
            "ManagedBy": [{"@odata.id": "/redfish/v1/Managers/HawkFish"}],
            "Systems": {"@odata.id": "/redfish/v1/Systems"},
        },
    }


