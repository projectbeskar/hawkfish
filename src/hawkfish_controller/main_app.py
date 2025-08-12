import os

import structlog
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api.audit import router as audit_router
from .api.batch import router as batch_router
from .api.chassis import router as chassis_router
from .api.console import router as console_router
from .api.hosts import router as hosts_router
from .api.images import router as images_router
from .api.import_adopt import router as import_router
from .api.ipxe import router as ipxe_router
from .api.managers import router as managers_router
from .api.netprofiles import router as netprofiles_router
from .api.orchestrator import router as orchestrator_router
from .api.persona import router as persona_router
from .api.profiles import router as profiles_router
from .api.projects import router as projects_router
from .api.service_root import router as service_root_router
from .api.sessions import router as sessions_router
from .api.snapshots import router as snapshots_router
from .api.storage import pools_router, volumes_router, system_volumes_router
from .api.systems import router as systems_router
from .api.task_event import router as task_event_router
from .api.update_service import router as update_service_router
from .config import ensure_directories, settings
from .middleware import MetricsLoggingMiddleware
from .rate_limit import RateLimitMiddleware
from .persona.registry import persona_registry
from .persona.hpe_ilo5 import hpe_ilo5_plugin


def create_app() -> FastAPI:
    app = FastAPI(
        title="HawkFish Controller",
        version="0.1.0",
        description=(
            "Redfish-compatible controller for KVM/libvirt. This API exposes a useful subset "
            "of Redfish for local labs."
        ),
        openapi_tags=[
            {"name": "ServiceRoot", "description": "Redfish Service Root"},
            {"name": "Systems", "description": "Computer Systems and power operations"},
            {"name": "Sessions", "description": "SessionService"},
            {"name": "Managers", "description": "Manager and VirtualMedia"},
            {"name": "Chassis", "description": "Logical chassis"},
            {"name": "Tasks", "description": "TaskService"},
            {"name": "Events", "description": "EventService"},
            {"name": "Orchestrator", "description": "Node lifecycle"},
            {"name": "Profiles", "description": "Reusable node specs"},
            {"name": "Batches", "description": "Batch provisioning"},
            {"name": "PXE", "description": "iPXE helper"},
            {"name": "Import", "description": "Import/adopt domains"},
            {"name": "Hosts", "description": "Host pool management"},
            {"name": "Images", "description": "Image catalog"},
            {"name": "NetworkProfiles", "description": "Network profile templates"},
            {"name": "UpdateService", "description": "Software inventory and updates"},
            {"name": "Snapshots", "description": "VM snapshots and backups"},
            {"name": "Projects", "description": "Multi-tenant projects"},
            {"name": "Console", "description": "Console access via WebSocket"},
            {"name": "Storage", "description": "Storage pools and volumes"},
        ],
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
    )

    ensure_directories()
    structlog.configure(processors=[structlog.processors.JSONRenderer()])
    app.add_middleware(MetricsLoggingMiddleware)
    # Only add rate limiting in non-dev mode
    if settings.auth_mode != "none":
        app.add_middleware(RateLimitMiddleware)

    # Register and mount persona plugins
    persona_registry.register_plugin(hpe_ilo5_plugin)
    persona_registry.mount_all(app)

    app.include_router(service_root_router)
    app.include_router(systems_router)
    app.include_router(sessions_router)
    app.include_router(managers_router)
    app.include_router(chassis_router)
    app.include_router(task_event_router)
    app.include_router(orchestrator_router)
    app.include_router(profiles_router)
    app.include_router(persona_router)
    app.include_router(batch_router)
    app.include_router(ipxe_router)
    app.include_router(import_router)
    app.include_router(hosts_router)
    app.include_router(images_router)
    app.include_router(netprofiles_router)
    app.include_router(update_service_router)
    app.include_router(snapshots_router)
    app.include_router(projects_router)
    app.include_router(console_router)
    app.include_router(pools_router)
    app.include_router(volumes_router)
    app.include_router(system_volumes_router)
    app.include_router(audit_router)

    # Serve UI if enabled
    if settings.ui_enabled:
        ui_dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ui', 'dist')
        if os.path.exists(ui_dist_path):
            app.mount("/ui", StaticFiles(directory=ui_dist_path, html=True), name="ui")
            
            @app.get("/ui/")
            async def serve_ui():
                index_path = os.path.join(ui_dist_path, 'index.html')
                return FileResponse(index_path)

    return app


