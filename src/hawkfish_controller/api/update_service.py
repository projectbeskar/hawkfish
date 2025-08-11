from __future__ import annotations

import sys

from fastapi import APIRouter, Depends

from .sessions import require_session

router = APIRouter(prefix="/redfish/v1/UpdateService", tags=["UpdateService"])


@router.get("")
def get_update_service(session=Depends(require_session)):
    """Get UpdateService details."""
    return {
        "@odata.type": "#UpdateService.v1_11_1.UpdateService",
        "@odata.id": "/redfish/v1/UpdateService",
        "Id": "UpdateService",
        "Name": "Update Service",
        "Description": "HawkFish Update Service",
        "Status": {
            "State": "Enabled",
            "Health": "OK"
        },
        "ServiceEnabled": True,
        "SoftwareInventory": {
            "@odata.id": "/redfish/v1/UpdateService/SoftwareInventory"
        },
        "Actions": {
            "#UpdateService.SimpleUpdate": {
                "target": "/redfish/v1/UpdateService/Actions/UpdateService.SimpleUpdate",
                "@Redfish.ActionInfo": "/redfish/v1/UpdateService/SimpleUpdateActionInfo"
            }
        }
    }


@router.get("/SoftwareInventory")
def list_software_inventory(session=Depends(require_session)):
    """List all software inventory items."""
    # Get versions - will be used in the individual endpoints
    
    members = [
        {"@odata.id": "/redfish/v1/UpdateService/SoftwareInventory/HawkFish"},
        {"@odata.id": "/redfish/v1/UpdateService/SoftwareInventory/Python"},
    ]
    
    return {
        "@odata.type": "#SoftwareInventoryCollection.SoftwareInventoryCollection",
        "@odata.id": "/redfish/v1/UpdateService/SoftwareInventory",
        "Name": "Software Inventory Collection",
        "Members@odata.count": len(members),
        "Members": members,
    }


@router.get("/SoftwareInventory/{software_id}")
def get_software_item(software_id: str, session=Depends(require_session)):
    """Get details for a specific software inventory item."""
    if software_id == "HawkFish":
        try:
            import hawkfish
            version = hawkfish.__version__
        except (ImportError, AttributeError):
            version = "unknown"
        
        return {
            "@odata.type": "#SoftwareInventory.v1_8_0.SoftwareInventory",
            "@odata.id": "/redfish/v1/UpdateService/SoftwareInventory/HawkFish",
            "Id": "HawkFish",
            "Name": "HawkFish Controller",
            "Description": "HawkFish Redfish Controller for KVM/libvirt",
            "Version": version,
            "Status": {
                "State": "Enabled",
                "Health": "OK"
            },
            "Updateable": False,
            "SoftwareId": "hawkfish-controller",
            "Manufacturer": "Project Beskar"
        }
    
    elif software_id == "Python":
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        return {
            "@odata.type": "#SoftwareInventory.v1_8_0.SoftwareInventory",
            "@odata.id": "/redfish/v1/UpdateService/SoftwareInventory/Python",
            "Id": "Python",
            "Name": "Python Runtime",
            "Description": "Python interpreter runtime",
            "Version": python_version,
            "Status": {
                "State": "Enabled",
                "Health": "OK"
            },
            "Updateable": False,
            "SoftwareId": "python-runtime"
        }
    
    else:
        from .errors import redfish_error
        return redfish_error("Software item not found", 404)


@router.post("/Actions/UpdateService.SimpleUpdate")
def simple_update(body: dict, session=Depends(require_session)):
    """Simple update action (read-only for now)."""
    from fastapi import HTTPException

    from ..services.security import require_role
    
    if not require_role("admin", session.role):
        raise HTTPException(status_code=403, detail="Forbidden")
    
    # For now, return not implemented
    from .errors import redfish_error
    return redfish_error("Update operations not implemented", 501)
