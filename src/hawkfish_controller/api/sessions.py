import os
import time

from fastapi import APIRouter, Header, HTTPException, status

from ..config import settings
from ..services.users import set_user, user_count, verify_user
from ..services.sessions import Session, global_session_store

router = APIRouter(prefix="/redfish/v1/SessionService", tags=["Sessions"])


@router.get("")
def get_session_service():
    return {
        "Id": "SessionService",
        "Name": "Session Service",
        "Sessions": {"@odata.id": "/redfish/v1/SessionService/Sessions"},
    }


@router.post("/Sessions")
async def create_session(body: dict):
    username = body.get("UserName", "user")
    password = body.get("Password", "")
    # bootstrap: if no users exist, create a default admin with provided password or 'admin'
    if await user_count() == 0:
        await set_user(username or "admin", password or "admin", "admin")
    role = "viewer" if settings.auth_mode == "none" else await verify_user(username, password)
    if role is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    session = global_session_store.create_session(username, role)
    return {
        "Id": session.token,
        "Name": f"Session for {username}",
        "UserName": username,
        "Role": role,
        "@odata.id": f"/redfish/v1/SessionService/Sessions/{session.token}",
        "X-Auth-Token": session.token,
    }


def require_session(x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")) -> Session:
    if getattr(settings, 'auth_mode', None) == "none":
        # return a permissive session for local/test mode
        dev_token = os.environ.get("HF_DEV_TOKEN", "dev")
        return Session(token=dev_token, username="local", role="admin", created_at=0.0, expires_at=1e12, last_activity=time.time())  # type: ignore[name-defined]
    if not x_auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-Auth-Token")
    session = global_session_store.get(x_auth_token)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")
    return session


