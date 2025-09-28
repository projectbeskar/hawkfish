"""
Dell iDRAC9 persona plugin for vendor compatibility.

This plugin provides Dell iDRAC-compatible endpoints and adapts responses
while maintaining clear disclaimers that this is not genuine Dell software.
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, FastAPI, HTTPException

from ..api.sessions import require_session
from ..config import settings
from ..drivers.libvirt_driver import LibvirtDriver, get_driver
from ..services.bios import bios_service
from ..services.security import check_role


class DellIdrac9Plugin:
    """Dell iDRAC9 compatibility persona plugin."""
    
    name = "dell_idrac9"
    
    def __init__(self):
        self.router = APIRouter()
        self._setup_routes()
    
    def mount(self, app: FastAPI) -> None:
        """Mount Dell iDRAC9 routes to the FastAPI app."""
        app.include_router(self.router, tags=["Dell iDRAC9 Compatibility"])
    
    def adapt_event(self, core_event: dict[str, Any]) -> list[dict[str, Any]]:
        """Adapt core events to Dell iDRAC9 format."""
        adapted = core_event.copy()
        
        # Add Dell-specific event fields
        adapted["Oem"] = adapted.get("Oem", {})
        adapted["Oem"]["Dell"] = {
            "EventID": f"dell_{core_event.get('EventType', 'unknown')}_{uuid.uuid4().hex[:8]}",
            "Category": self._map_event_category(core_event.get("EventType", "")),
            "Source": "iDRAC",
            "Severity": core_event.get("Severity", "OK")
        }
        
        # Add compatibility disclaimer
        adapted["Oem"]["HawkFish"] = {
            "CompatibilityDisclaimer": "HawkFish Dell iDRAC compatibility mode for testing; not affiliated with Dell."
        }
        
        return [adapted]
    
    def adapt_error(self, core_error: dict[str, Any]) -> dict[str, Any]:
        """Adapt core errors to Dell iDRAC9 format."""
        adapted = core_error.copy()
        
        # Map to Dell message IDs where applicable
        message_id = core_error.get("@Message.MessageId", "")
        if "InvalidAttribute" in message_id:
            adapted["@Message.MessageId"] = "Oem.Dell.BIOS.InvalidAttribute"
        elif "RequiresPowerOff" in message_id:
            adapted["@Message.MessageId"] = "Oem.Dell.BIOS.RequiresPowerOff"
        elif "DeviceUnavailable" in message_id:
            adapted["@Message.MessageId"] = "Oem.Dell.Media.DeviceUnavailable"
        
        # Add Dell OEM error details
        adapted["Oem"] = adapted.get("Oem", {})
        adapted["Oem"]["Dell"] = {
            "MessageRegistry": "Dell.1.0.0",
            "MessageSource": "iDRAC",
            "Resolution": adapted.get("Resolution", "Review the request and try again.")
        }
        
        return adapted
    
    def _setup_routes(self) -> None:
        """Set up Dell iDRAC9 compatibility routes."""
        
        @self.router.get("/redfish/v1/Managers/iDRAC.Embedded.1")
        async def get_idrac_manager(session=Depends(require_session)):
            """Get Dell iDRAC Manager resource."""
            return {
                "@odata.type": "#Manager.v1_10_0.Manager",
                "@odata.id": "/redfish/v1/Managers/iDRAC.Embedded.1",
                "Id": "iDRAC.Embedded.1",
                "Name": "Manager",
                "ManagerType": "BMC",
                "Manufacturer": "HawkFish (Dell iDRAC-compatible mode)",
                "Model": "Integrated Dell Remote Access Controller 9",
                "FirmwareVersion": f"HawkFish-{settings.version}-idrac9",
                "Status": {
                    "State": "Enabled",
                    "Health": "OK"
                },
                "Links": {
                    "VirtualMedia": {
                        "@odata.id": "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia"
                    }
                },
                "Oem": {
                    "Dell": {
                        "DellManager": {
                            "DellManagerType": "iDRAC",
                            "iDRACVersion": "4.40.00.00"
                        }
                    },
                    "HawkFish": {
                        "CompatibilityDisclaimer": "HawkFish Dell iDRAC compatibility mode for testing; not affiliated with Dell."
                    }
                }
            }
        
        @self.router.get("/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia")
        async def get_idrac_virtual_media_collection(session=Depends(require_session)):
            """Get Dell iDRAC VirtualMedia collection."""
            return {
                "@odata.type": "#VirtualMediaCollection.VirtualMediaCollection",
                "@odata.id": "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia",
                "Name": "Virtual Media Services",
                "Members": [
                    {"@odata.id": "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD"}
                ],
                "Members@odata.count": 1,
                "Oem": {
                    "HawkFish": {
                        "CompatibilityDisclaimer": "HawkFish Dell iDRAC compatibility mode for testing; not affiliated with Dell."
                    }
                }
            }
        
        @self.router.get("/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD")
        async def get_idrac_virtual_media_cd(session=Depends(require_session)):
            """Get Dell iDRAC CD VirtualMedia resource."""
            return {
                "@odata.type": "#VirtualMedia.v1_3_0.VirtualMedia",
                "@odata.id": "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD",
                "Id": "CD",
                "Name": "Virtual CD",
                "MediaTypes": ["CD", "DVD"],
                "Inserted": False,
                "WriteProtected": True,
                "ConnectedVia": "NotConnected",
                "Actions": {
                    "Oem": {
                        "DellVirtualMedia.v1_0_0#DellVirtualMedia.InsertVirtualMedia": {
                            "target": "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/Oem/DellVirtualMedia.InsertVirtualMedia"
                        },
                        "DellVirtualMedia.v1_0_0#DellVirtualMedia.EjectVirtualMedia": {
                            "target": "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/Oem/DellVirtualMedia.EjectVirtualMedia"
                        }
                    }
                },
                "Oem": {
                    "HawkFish": {
                        "CompatibilityDisclaimer": "HawkFish Dell iDRAC compatibility mode for testing; not affiliated with Dell."
                    }
                }
            }
        
        @self.router.post("/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/Oem/DellVirtualMedia.InsertVirtualMedia")
        async def idrac_insert_virtual_media(
            body: dict,
            driver: LibvirtDriver = Depends(get_driver),
            session=Depends(require_session)
        ):
            """Insert virtual media via Dell iDRAC compatibility endpoint."""
            if not check_role("operator", session.role):
                raise HTTPException(status_code=403, detail="Forbidden")
            
            # Map Dell request to HawkFish format
            system_id = body.get("SystemId") or body.get("Target")
            image_url = body.get("Image")
            
            if not system_id or not image_url:
                raise HTTPException(
                    status_code=400,
                    detail="SystemId/Target and Image are required"
                )
            
            # Delegate to core VirtualMedia logic
            from ..api.managers import insert_media
            core_body = {
                "SystemId": system_id,
                "Image": image_url
            }
            
            result = insert_media(core_body, driver, session)
            
            # Add Dell-specific response formatting
            if isinstance(result, dict):
                result["Oem"] = {
                    "Dell": {
                        "JobStatus": "Completed" if result.get("TaskState") == "Completed" else "Running"
                    },
                    "HawkFish": {
                        "CompatibilityDisclaimer": "HawkFish Dell iDRAC compatibility mode for testing; not affiliated with Dell."
                    }
                }
            
            return result
        
        @self.router.post("/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/Oem/DellVirtualMedia.EjectVirtualMedia")
        async def idrac_eject_virtual_media(
            body: dict,
            driver: LibvirtDriver = Depends(get_driver),
            session=Depends(require_session)
        ):
            """Eject virtual media via Dell iDRAC compatibility endpoint."""
            if not check_role("operator", session.role):
                raise HTTPException(status_code=403, detail="Forbidden")
            
            # Map Dell request to HawkFish format
            system_id = body.get("SystemId") or body.get("Target")
            
            if not system_id:
                raise HTTPException(
                    status_code=400,
                    detail="SystemId/Target is required"
                )
            
            # Delegate to core VirtualMedia logic
            from ..api.managers import eject_media
            core_body = {"SystemId": system_id}
            
            result = eject_media(core_body, driver, session)
            
            # Add Dell-specific response formatting
            if isinstance(result, dict):
                result["Oem"] = {
                    "Dell": {
                        "JobStatus": "Completed" if result.get("TaskState") == "Completed" else "Running"
                    },
                    "HawkFish": {
                        "CompatibilityDisclaimer": "HawkFish Dell iDRAC compatibility mode for testing; not affiliated with Dell."
                    }
                }
            
            return result
        
        @self.router.get("/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs")
        async def get_idrac_jobs(session=Depends(require_session)):
            """Get Dell iDRAC Jobs (mapped from TaskService)."""
            from ..services.tasks import TaskService
            
            try:
                task_service = TaskService()
                tasks = await task_service.list_tasks()
                
                # Convert HawkFish tasks to Dell Job format
                jobs = []
                for task in tasks:
                    jobs.append({
                        "@odata.id": f"/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/{task.id}"
                    })
                
                return {
                    "@odata.type": "#DellJobCollection.DellJobCollection",
                    "@odata.id": "/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs",
                    "Name": "Dell Job Queue",
                    "Members": jobs,
                    "Members@odata.count": len(jobs),
                    "Oem": {
                        "HawkFish": {
                            "CompatibilityDisclaimer": "HawkFish Dell iDRAC compatibility mode for testing; not affiliated with Dell.",
                            "Note": "Jobs are mapped from HawkFish TaskService"
                        }
                    }
                }
            except Exception as e:
                # Return empty collection on error
                return {
                    "@odata.type": "#DellJobCollection.DellJobCollection",
                    "@odata.id": "/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs",
                    "Name": "Dell Job Queue",
                    "Members": [],
                    "Members@odata.count": 0,
                    "Oem": {
                        "HawkFish": {
                            "CompatibilityDisclaimer": "HawkFish Dell iDRAC compatibility mode for testing; not affiliated with Dell.",
                            "Error": f"Failed to retrieve jobs: {str(e)}"
                        }
                    }
                }
        
        @self.router.get("/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/{job_id}")
        async def get_idrac_job(job_id: str, session=Depends(require_session)):
            """Get specific Dell iDRAC Job (mapped from TaskService)."""
            from ..services.tasks import TaskService
            
            try:
                task_service = TaskService()
                task = await task_service.get_task(job_id)
                
                if not task:
                    raise HTTPException(status_code=404, detail="Job not found")
                
                job = self._convert_task_to_dell_job(task)
                job["@odata.id"] = f"/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/{job_id}"
                job["Oem"] = {
                    "HawkFish": {
                        "CompatibilityDisclaimer": "HawkFish Dell iDRAC compatibility mode for testing; not affiliated with Dell.",
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
                "AttributeRegistry": "DellBiosAttributeRegistry.v1_0_0",
                "Attributes": current_attrs,
                "Links": {
                    "Settings": {
                        "@odata.id": f"/redfish/v1/Systems/{system_id}/Bios/Settings"
                    }
                },
                "Oem": {
                    "Dell": {
                        "BIOSConfig": {
                            "PendingChanges": pending is not None
                        }
                    },
                    "HawkFish": {
                        "CompatibilityDisclaimer": "HawkFish Dell iDRAC compatibility mode for testing; not affiliated with Dell."
                    }
                }
            }
        
        @self.router.patch("/redfish/v1/Systems/{system_id}/Bios/Settings")
        async def patch_system_bios_settings(
            system_id: str,
            body: dict,
            session=Depends(require_session)
        ):
            """Update BIOS settings with Dell iDRAC ApplyTime support."""
            if not check_role("operator", session.role):
                raise HTTPException(status_code=403, detail="Forbidden")
            
            attributes = body.get("Attributes", {})
            # Dell uses different OEM structure for ApplyTime
            oem_dell = body.get("Oem", {}).get("Dell", {})
            apply_time = oem_dell.get("ApplyTime", "OnReset")
            
            if not attributes:
                raise HTTPException(
                    status_code=400,
                    detail="Attributes are required"
                )
            
            try:
                # Stage the changes using core BIOS service
                await bios_service.stage_bios_changes(
                    system_id, attributes, apply_time, session.user_id
                )
                
                return {
                    "TaskState": "Completed" if apply_time == "Immediate" else "Pending",
                    "Message": f"BIOS settings will be applied {apply_time.lower()}",
                    "Oem": {
                        "Dell": {
                            "ApplyTime": apply_time,
                            "BIOSConfig": {
                                "JobType": "BIOSConfiguration"
                            }
                        },
                        "HawkFish": {
                            "CompatibilityDisclaimer": "HawkFish Dell iDRAC compatibility mode for testing; not affiliated with Dell."
                        }
                    }
                }
                
            except Exception as e:
                from ..services.bios import BiosValidationError, BiosApplyTimeError
                from ..services.message_registry import hpe_message_registry
                
                # Handle Dell-specific BIOS errors
                if isinstance(e, (BiosValidationError, BiosApplyTimeError)):
                    # Convert HPE message IDs to Dell equivalents
                    dell_message_id = e.message_id.replace("Oem.Hpe.", "Oem.Dell.")
                    
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": {
                                "code": dell_message_id,
                                "message": str(e),
                                "@Message.ExtendedInfo": [{
                                    "MessageId": dell_message_id,
                                    "Message": str(e),
                                    "Severity": "Warning",
                                    "Resolution": "Check BIOS attribute values and system state."
                                }]
                            }
                        }
                    )
                else:
                    # Generic error
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": {
                                "code": "Oem.Dell.BIOS.InvalidAttribute",
                                "message": str(e),
                                "@Message.ExtendedInfo": [{
                                    "MessageId": "Oem.Dell.BIOS.InvalidAttribute",
                                    "Message": f"Invalid BIOS attribute: {e}",
                                    "Resolution": "Check the attribute name and value against the BIOS registry.",
                                    "Severity": "Warning"
                                }]
                            }
                        }
                    )
    
    def _convert_task_to_dell_job(self, task) -> dict[str, Any]:
        """Convert HawkFish Task to Dell Job format."""
        # Map HawkFish task states to Dell Job states
        state_mapping = {
            "pending": "Scheduled",
            "running": "Running", 
            "completed": "Completed",
            "failed": "Failed",
            "cancelled": "Failed"
        }
        
        job_state = state_mapping.get(task.state, "Scheduled")
        
        # Calculate percentage complete
        percent_complete = 0
        if task.state == "completed":
            percent_complete = 100
        elif task.state == "running" and hasattr(task, 'progress'):
            percent_complete = min(int(task.progress * 100), 99)
        
        # Format timestamps
        start_time = task.created_at if hasattr(task, 'created_at') else None
        end_time = task.completed_at if hasattr(task, 'completed_at') and task.state in ["completed", "failed", "cancelled"] else None
        
        return {
            "@odata.type": "#DellJob.v1_0_0.DellJob",
            "Id": task.id,
            "Name": task.name or f"Job {task.id}",
            "JobState": job_state,
            "PercentComplete": percent_complete,
            "StartTime": start_time,
            "EndTime": end_time,
            "Message": task.message or f"Job {task.state}",
            "JobType": "Configuration"
        }
    
    def _map_event_category(self, event_type: str) -> str:
        """Map HawkFish event types to Dell categories."""
        mapping = {
            "PowerStateChanged": "System",
            "MediaInserted": "VirtualMedia", 
            "MediaEjected": "VirtualMedia",
            "BiosSettingsApplied": "BIOS",
            "SystemCreated": "System",
            "SystemDeleted": "System"
        }
        return mapping.get(event_type, "General")


# Plugin instance
dell_idrac9_plugin = DellIdrac9Plugin()
