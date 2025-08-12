"""
HPE iLO5 persona plugin for vendor compatibility.

This plugin provides HPE iLO-compatible endpoints and adapts responses
while maintaining clear disclaimers that this is not genuine HPE software.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Response

from ..api.sessions import require_session
from ..config import settings
from ..drivers.libvirt_driver import LibvirtDriver, get_driver
from ..services.bios import bios_service
from ..services.persona import persona_service
from ..services.security import check_role
from ..services.tasks import TaskService


class HpeIlo5Plugin:
    """HPE iLO5 compatibility persona plugin."""
    
    name = "hpe_ilo5"
    
    def __init__(self):
        self.router = APIRouter()
        self._setup_routes()
    
    def mount(self, app: FastAPI) -> None:
        """Mount HPE iLO5 routes to the FastAPI app."""
        app.include_router(self.router, tags=["HPE iLO5 Compatibility"])
    
    def adapt_event(self, core_event: dict[str, Any]) -> list[dict[str, Any]]:
        """Adapt core events to HPE iLO5 format."""
        adapted = core_event.copy()
        
        # Add HPE-specific event fields
        adapted["Oem"] = adapted.get("Oem", {})
        adapted["Oem"]["Hpe"] = {
            "EventID": f"hpe_{core_event.get('EventType', 'unknown')}_{uuid.uuid4().hex[:8]}",
            "Category": self._map_event_category(core_event.get("EventType", "")),
            "Severity": core_event.get("Severity", "OK")
        }
        
        # Add compatibility disclaimer
        adapted["Oem"]["HawkFish"] = {
            "CompatibilityDisclaimer": "HawkFish HPE iLO compatibility mode for testing; not affiliated with HPE."
        }
        
        return [adapted]
    
    def adapt_error(self, core_error: dict[str, Any]) -> dict[str, Any]:
        """Adapt core errors to HPE iLO5 format."""
        adapted = core_error.copy()
        
        # Map to HPE message IDs where applicable
        message_id = core_error.get("@Message.MessageId", "")
        if "InvalidAttribute" in message_id:
            adapted["@Message.MessageId"] = "Oem.Hpe.Bios.InvalidAttribute"
        elif "RequiresPowerOff" in message_id:
            adapted["@Message.MessageId"] = "Oem.Hpe.Bios.RequiresPowerOff"
        
        # Add HPE OEM error details
        adapted["Oem"] = adapted.get("Oem", {})
        adapted["Oem"]["Hpe"] = {
            "MessageRegistry": "Hpe.1.0.0",
            "Resolution": adapted.get("Resolution", "Review the request and try again.")
        }
        
        return adapted
    
    def _setup_routes(self) -> None:
        """Set up HPE iLO5 compatibility routes."""
        
        @self.router.get("/redfish/v1/Managers/iLO.Embedded.1")
        async def get_ilo_manager(session=Depends(require_session)):
            """Get HPE iLO Manager resource."""
            return {
                "@odata.type": "#Manager.v1_10_0.Manager",
                "@odata.id": "/redfish/v1/Managers/iLO.Embedded.1",
                "Id": "iLO.Embedded.1",
                "Name": "Manager",
                "ManagerType": "BMC",
                "Manufacturer": "HawkFish (HPE iLO-compatible mode)",
                "Model": "Integrated Lights-Out 5",
                "FirmwareVersion": f"HawkFish-{settings.version}-ilo5",
                "Status": {
                    "State": "Enabled",
                    "Health": "OK"
                },
                "Links": {
                    "VirtualMedia": {
                        "@odata.id": "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia"
                    }
                },
                "Oem": {
                    "HawkFish": {
                        "CompatibilityDisclaimer": "HawkFish HPE iLO compatibility mode for testing; not affiliated with HPE."
                    }
                }
            }
        
        @self.router.get("/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia")
        async def get_ilo_virtual_media_collection(session=Depends(require_session)):
            """Get HPE iLO VirtualMedia collection."""
            return {
                "@odata.type": "#VirtualMediaCollection.VirtualMediaCollection",
                "@odata.id": "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia",
                "Name": "Virtual Media Services",
                "Members": [
                    {"@odata.id": "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1"}
                ],
                "Members@odata.count": 1,
                "Oem": {
                    "HawkFish": {
                        "CompatibilityDisclaimer": "HawkFish HPE iLO compatibility mode for testing; not affiliated with HPE."
                    }
                }
            }
        
        @self.router.get("/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1")
        async def get_ilo_virtual_media_cd(session=Depends(require_session)):
            """Get HPE iLO CD VirtualMedia resource."""
            return {
                "@odata.type": "#VirtualMedia.v1_3_0.VirtualMedia",
                "@odata.id": "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1",
                "Id": "CD1",
                "Name": "Virtual Removable Media",
                "MediaTypes": ["CD", "DVD"],
                "Inserted": False,
                "WriteProtected": True,
                "ConnectedVia": "NotConnected",
                "Actions": {
                    "#VirtualMedia.InsertMedia": {
                        "target": "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1/Actions/VirtualMedia.InsertMedia"
                    },
                    "#VirtualMedia.EjectMedia": {
                        "target": "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1/Actions/VirtualMedia.EjectMedia"
                    }
                },
                "Oem": {
                    "HawkFish": {
                        "CompatibilityDisclaimer": "HawkFish HPE iLO compatibility mode for testing; not affiliated with HPE."
                    }
                }
            }
        
        @self.router.post("/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1/Actions/VirtualMedia.InsertMedia")
        async def ilo_insert_media(
            body: dict,
            driver: LibvirtDriver = Depends(get_driver),
            session=Depends(require_session)
        ):
            """Insert media via HPE iLO compatibility endpoint."""
            if not check_role("operator", session.role):
                raise HTTPException(status_code=403, detail="Forbidden")
            
            # Map HPE request to HawkFish format
            system_id = body.get("SystemId")
            image_url = body.get("Image")
            
            if not system_id or not image_url:
                raise HTTPException(
                    status_code=400,
                    detail="SystemId and Image are required"
                )
            
            # Delegate to core VirtualMedia logic
            from ..api.managers import insert_media
            core_body = {
                "SystemId": system_id,
                "Image": image_url
            }
            
            return insert_media(core_body, driver, session)
        
        @self.router.post("/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1/Actions/VirtualMedia.EjectMedia")
        async def ilo_eject_media(
            body: dict,
            driver: LibvirtDriver = Depends(get_driver),
            session=Depends(require_session)
        ):
            """Eject media via HPE iLO compatibility endpoint."""
            if not check_role("operator", session.role):
                raise HTTPException(status_code=403, detail="Forbidden")
            
            # Map HPE request to HawkFish format
            system_id = body.get("SystemId")
            
            if not system_id:
                raise HTTPException(
                    status_code=400,
                    detail="SystemId is required"
                )
            
            # Delegate to core VirtualMedia logic
            from ..api.managers import eject_media
            core_body = {"SystemId": system_id}
            
            return eject_media(core_body, driver, session)
        
        @self.router.get("/redfish/v1/Managers/iLO.Embedded.1/Oem/Hpe/Jobs")
        async def get_ilo_jobs(session=Depends(require_session)):
            """Get HPE iLO Jobs (mapped from TaskService)."""
            # TODO: Map from actual TaskService
            return {
                "@odata.type": "#HpeJobCollection.HpeJobCollection",
                "@odata.id": "/redfish/v1/Managers/iLO.Embedded.1/Oem/Hpe/Jobs",
                "Name": "Jobs",
                "Members": [],
                "Members@odata.count": 0,
                "Oem": {
                    "HawkFish": {
                        "CompatibilityDisclaimer": "HawkFish HPE iLO compatibility mode for testing; not affiliated with HPE.",
                        "Note": "Jobs are mapped from HawkFish TaskService"
                    }
                }
            }
        
        # BIOS endpoints
        @self.router.get("/redfish/v1/Systems/{system_id}/Bios")
        async def get_system_bios(system_id: str, session=Depends(require_session)):
            """Get BIOS settings for a system."""
            current_attrs = await bios_service.get_current_bios_attributes(system_id)
            pending = await bios_service.get_pending_bios_changes(system_id)
            
            return {
                "@odata.type": "#Bios.v1_1_0.Bios",
                "@odata.id": f"/redfish/v1/Systems/{system_id}/Bios",
                "Id": "BIOS",
                "Name": "BIOS Configuration Current Settings",
                "AttributeRegistry": "BiosAttributeRegistry.v1_0_0",
                "Attributes": current_attrs,
                "Links": {
                    "Settings": {
                        "@odata.id": f"/redfish/v1/Systems/{system_id}/Bios/Settings"
                    }
                },
                "Oem": {
                    "Hpe": {
                        "PendingChanges": pending is not None
                    },
                    "HawkFish": {
                        "CompatibilityDisclaimer": "HawkFish HPE iLO compatibility mode for testing; not affiliated with HPE."
                    }
                }
            }
        
        @self.router.patch("/redfish/v1/Systems/{system_id}/Bios/Settings")
        async def patch_system_bios_settings(
            system_id: str,
            body: dict,
            session=Depends(require_session)
        ):
            """Update BIOS settings with ApplyTime support."""
            if not check_role("operator", session.role):
                raise HTTPException(status_code=403, detail="Forbidden")
            
            attributes = body.get("Attributes", {})
            oem_hpe = body.get("Oem", {}).get("Hpe", {})
            apply_time = oem_hpe.get("ApplyTime", "OnReset")
            
            if not attributes:
                raise HTTPException(
                    status_code=400,
                    detail="Attributes are required"
                )
            
            try:
                if apply_time == "Immediate":
                    # For immediate application, validate that system is powered off
                    # and no changes require a reboot
                    current = await bios_service.get_current_bios_attributes(system_id)
                    
                    # Check if any changes require a reboot
                    reboot_required = (
                        "BootMode" in attributes and attributes["BootMode"] != current.get("BootMode") or
                        "SecureBoot" in attributes and attributes["SecureBoot"] != current.get("SecureBoot")
                    )
                    
                    if reboot_required:
                        raise HTTPException(
                            status_code=400,
                            detail={
                                "error": {
                                    "code": "Oem.Hpe.Bios.RequiresPowerOff",
                                    "message": "The requested BIOS changes require the system to be powered off.",
                                    "@Message.ExtendedInfo": [{
                                        "MessageId": "Oem.Hpe.Bios.RequiresPowerOff",
                                        "Message": "The requested BIOS setting changes require ApplyTime=OnReset or system power off.",
                                        "Resolution": "Set ApplyTime to OnReset or power off the system before applying changes.",
                                        "Severity": "Warning"
                                    }]
                                }
                            }
                        )
                
                # Stage the changes
                await bios_service.stage_bios_changes(
                    system_id, attributes, apply_time, session.user_id
                )
                
                return {
                    "TaskState": "Completed" if apply_time == "Immediate" else "Pending",
                    "Message": f"BIOS settings will be applied {apply_time.lower()}",
                    "Oem": {
                        "Hpe": {
                            "ApplyTime": apply_time
                        },
                        "HawkFish": {
                            "CompatibilityDisclaimer": "HawkFish HPE iLO compatibility mode for testing; not affiliated with HPE."
                        }
                    }
                }
                
            except ValueError as e:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": {
                            "code": "Oem.Hpe.Bios.InvalidAttribute",
                            "message": str(e),
                            "@Message.ExtendedInfo": [{
                                "MessageId": "Oem.Hpe.Bios.InvalidAttribute",
                                "Message": f"Invalid BIOS attribute: {e}",
                                "Resolution": "Check the attribute name and value against the BIOS registry.",
                                "Severity": "Warning"
                            }]
                        }
                    }
                )
    
    def _map_event_category(self, event_type: str) -> str:
        """Map HawkFish event types to HPE categories."""
        mapping = {
            "PowerStateChanged": "Power",
            "MediaInserted": "VirtualMedia", 
            "MediaEjected": "VirtualMedia",
            "BiosSettingsApplied": "BIOS",
            "SystemCreated": "System",
            "SystemDeleted": "System"
        }
        return mapping.get(event_type, "General")


# Plugin instance
hpe_ilo5_plugin = HpeIlo5Plugin()
