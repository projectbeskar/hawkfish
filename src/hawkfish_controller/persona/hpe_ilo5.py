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
            from ..api.task_event import get_task_service
            
            core_body = {
                "SystemId": system_id,
                "Image": image_url
            }
            
            # Get task service for direct function call
            task_service = get_task_service()
            
            return await insert_media(core_body, driver, session, task_service)
        
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
            
            return await eject_media(core_body, driver, session)
        
        @self.router.get("/redfish/v1/Managers/iLO.Embedded.1/Oem/Hpe/Jobs")
        async def get_ilo_jobs(session=Depends(require_session)):
            """Get HPE iLO Jobs (mapped from TaskService)."""
            
            try:
                task_service = TaskService()
                tasks = await task_service.list_tasks()
                
                # Convert HawkFish tasks to HPE Job format
                jobs = []
                for task in tasks:
                    jobs.append({
                        "@odata.id": f"/redfish/v1/Managers/iLO.Embedded.1/Oem/Hpe/Jobs/{task.id}"
                    })
                
                return {
                    "@odata.type": "#HpeJobCollection.HpeJobCollection",
                    "@odata.id": "/redfish/v1/Managers/iLO.Embedded.1/Oem/Hpe/Jobs",
                    "Name": "Jobs",
                    "Members": jobs,
                    "Members@odata.count": len(jobs),
                    "Oem": {
                        "HawkFish": {
                            "CompatibilityDisclaimer": "HawkFish HPE iLO compatibility mode for testing; not affiliated with HPE.",
                            "Note": "Jobs are mapped from HawkFish TaskService"
                        }
                    }
                }
            except Exception as e:
                # Return empty collection on error
                return {
                    "@odata.type": "#HpeJobCollection.HpeJobCollection",
                    "@odata.id": "/redfish/v1/Managers/iLO.Embedded.1/Oem/Hpe/Jobs",
                    "Name": "Jobs",
                    "Members": [],
                    "Members@odata.count": 0,
                    "Oem": {
                        "HawkFish": {
                            "CompatibilityDisclaimer": "HawkFish HPE iLO compatibility mode for testing; not affiliated with HPE.",
                            "Note": "Jobs are mapped from HawkFish TaskService",
                            "Error": f"Failed to retrieve tasks: {str(e)}"
                        }
                    }
                }
        
        @self.router.get("/redfish/v1/Managers/iLO.Embedded.1/Oem/Hpe/Jobs/{job_id}")
        async def get_ilo_job(job_id: str, session=Depends(require_session)):
            """Get specific HPE iLO Job (mapped from TaskService)."""
            
            try:
                task_service = TaskService()
                task = await task_service.get_task(job_id)
                
                if not task:
                    raise HTTPException(status_code=404, detail="Job not found")
                
                job = self._convert_task_to_hpe_job(task)
                job["@odata.id"] = f"/redfish/v1/Managers/iLO.Embedded.1/Oem/Hpe/Jobs/{job_id}"
                job["Oem"] = {
                    "HawkFish": {
                        "CompatibilityDisclaimer": "HawkFish HPE iLO compatibility mode for testing; not affiliated with HPE.",
                        "Note": "Job is mapped from HawkFish Task",
                        "OriginalTaskId": task.id
                    }
                }
                
                return job
                
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to retrieve job: {str(e)}"
                )
        
        @self.router.post("/redfish/v1/Managers/iLO.Embedded.1/Oem/Hpe/Actions/Hpe.iLO.LaunchConsole")
        async def launch_ilo_console(
            body: dict,
            session=Depends(require_session)
        ):
            """Launch console session via HPE iLO endpoint."""
            if not check_role("operator", session.role):
                raise HTTPException(status_code=403, detail="Forbidden")
            
            # Get protocol and system from request
            protocol = body.get("Protocol", "VNC")
            system_id = body.get("SystemId")
            
            if not system_id:
                raise HTTPException(
                    status_code=400,
                    detail="SystemId is required"
                )
            
            # Validate protocol
            valid_protocols = ["VNC", "Serial"]
            if protocol not in valid_protocols:
                raise HTTPException(
                    status_code=400,
                    detail=f"Protocol must be one of: {', '.join(valid_protocols)}"
                )
            
            # Create console session using HawkFish console service
            from ..services.console import console_service
            
            try:
                console_session = await console_service.create_session(
                    system_id=system_id,
                    protocol=protocol.lower(),
                    user_id=session.user_id
                )
                
                # Construct WebSocket URL
                base_url = settings.base_url or "wss://localhost:8080"
                if base_url.startswith("http"):
                    base_url = base_url.replace("http", "ws")
                
                ws_url = f"{base_url}/ws/console/{console_session.token}"
                
                return {
                    "ConsoleSession": {
                        "Id": console_session.token,
                        "Protocol": protocol,
                        "URI": ws_url,
                        "ExpiresAt": console_session.expires_at,
                        "SystemId": system_id
                    },
                    "Oem": {
                        "Hpe": {
                            "SessionType": "RemoteConsole",
                            "LaunchType": "HTML5"
                        },
                        "HawkFish": {
                            "CompatibilityDisclaimer": "HawkFish HPE iLO compatibility mode for testing; not affiliated with HPE.",
                            "Note": "Console session mapped to HawkFish console service"
                        }
                    }
                }
                
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to create console session: {str(e)}"
                )
        
        @self.router.delete("/redfish/v1/Managers/iLO.Embedded.1/Oem/Hpe/ConsoleSessions/{token}")
        async def revoke_ilo_console_session(
            token: str,
            session=Depends(require_session)
        ):
            """Revoke console session via HPE iLO endpoint."""
            if not check_role("operator", session.role):
                raise HTTPException(status_code=403, detail="Forbidden")
            
            # Revoke using HawkFish console service
            from ..services.console import console_service
            
            try:
                await console_service.revoke_session(token)
                return {
                    "TaskState": "Completed",
                    "Message": "Console session revoked",
                    "Oem": {
                        "HawkFish": {
                            "CompatibilityDisclaimer": "HawkFish HPE iLO compatibility mode for testing; not affiliated with HPE."
                        }
                    }
                }
            except Exception as e:
                raise HTTPException(
                    status_code=404,
                    detail=f"Console session not found: {str(e)}"
                )
        
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
                        from ..services.bios import BiosApplyTimeError
                        raise BiosApplyTimeError("Oem.Hpe.Bios.RequiresPowerOff")
                
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
                
            except Exception as e:
                from ..services.bios import BiosValidationError, BiosApplyTimeError
                from ..services.message_registry import hpe_message_registry
                
                # Handle HPE-specific BIOS errors
                if isinstance(e, (BiosValidationError, BiosApplyTimeError)):
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": {
                                "code": e.message_id,
                                "message": str(e),
                                "@Message.ExtendedInfo": [e.message_info]
                            }
                        }
                    )
                else:
                    # Generic error
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": {
                                "code": "Oem.Hpe.Bios.InvalidAttribute",
                                "message": str(e),
                                "@Message.ExtendedInfo": hpe_message_registry.create_extended_info(
                                    "Oem.Hpe.Bios.InvalidAttribute", 
                                    ["General", str(e)]
                                )
                            }
                        }
                    )
    
    def _convert_task_to_hpe_job(self, task) -> dict[str, Any]:
        """Convert HawkFish Task to HPE Job format."""
        # Map HawkFish task states to HPE Job states
        state_mapping = {
            "pending": "Running",
            "running": "Running", 
            "completed": "Completed",
            "failed": "Exception",
            "cancelled": "Exception"
        }
        
        job_state = state_mapping.get(task.state, "Running")
        
        # Calculate percentage complete
        percent_complete = 0
        if task.state == "completed":
            percent_complete = 100
        elif task.state == "running" and hasattr(task, 'progress'):
            percent_complete = min(int(task.progress * 100), 99)  # Never 100% until completed
        
        # Format timestamps
        start_time = task.created_at if hasattr(task, 'created_at') else None
        end_time = task.completed_at if hasattr(task, 'completed_at') and task.state in ["completed", "failed", "cancelled"] else None
        
        return {
            "@odata.type": "#HpeJob.v1_0_0.HpeJob",
            "Id": task.id,
            "Name": task.name or f"Task {task.id}",
            "JobState": job_state,
            "PercentComplete": percent_complete,
            "StartTime": start_time,
            "EndTime": end_time,
            "Message": task.message or f"Task {task.state}",
            "RelatedItem": {
                "@odata.id": f"/redfish/v1/TaskService/Tasks/{task.id}"
            }
        }
    
    def _map_event_category(self, event_type: str) -> str:
        """Map HawkFish event types to HPE categories."""
        mapping = {
            "PowerStateChanged": "Power",
            "MediaInserted": "VirtualMedia", 
            "MediaEjected": "VirtualMedia",
            "BiosSettingsApplied": "System BIOS",
            "SystemCreated": "System",
            "SystemDeleted": "System"
        }
        return mapping.get(event_type, "General")


# Plugin instance
hpe_ilo5_plugin = HpeIlo5Plugin()
