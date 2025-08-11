import structlog
from fastapi import FastAPI

from .api.chassis import router as chassis_router
from .api.managers import router as managers_router
from .api.orchestrator import router as orchestrator_router
from .api.service_root import router as service_root_router
from .api.sessions import router as sessions_router
from .api.systems import router as systems_router
from .api.task_event import router as task_event_router
from .config import ensure_directories, settings
from .middleware import MetricsLoggingMiddleware


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
        ],
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
    )

    ensure_directories()
    structlog.configure(processors=[structlog.processors.JSONRenderer()])
    app.add_middleware(MetricsLoggingMiddleware)

    app.include_router(service_root_router)
    app.include_router(systems_router)
    app.include_router(sessions_router)
    app.include_router(managers_router)
    app.include_router(chassis_router)
    app.include_router(task_event_router)
    app.include_router(orchestrator_router)

    return app


