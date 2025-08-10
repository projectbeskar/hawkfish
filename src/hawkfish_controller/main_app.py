from fastapi import FastAPI

from .api.managers import router as managers_router
from .api.service_root import router as service_root_router
from .api.sessions import router as sessions_router
from .api.systems import router as systems_router
from .api.task_event import router as task_event_router
from .config import settings


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
            {"name": "Tasks", "description": "TaskService"},
            {"name": "Events", "description": "EventService"},
        ],
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
    )

    app.include_router(service_root_router)
    app.include_router(systems_router)
    app.include_router(sessions_router)
    app.include_router(managers_router)
    app.include_router(task_event_router)

    return app


