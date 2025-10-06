import base64
import os
import time

from fastapi import APIRouter, Header, HTTPException, Request, status

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


async def require_session(
    request: Request,
    x_auth_token: str | None = Header(default=None, alias="X-Auth-Token"),
    authorization: str | None = Header(default=None)
) -> Session:
    """
    Require authentication via X-Auth-Token (sessions) or HTTP Basic Auth.
    Supports multiple authentication modes based on HF_AUTH setting.
    """
    # If auth is disabled, return permissive session
    if getattr(settings, 'auth_mode', None) == "none":
        dev_token = os.environ.get("HF_DEV_TOKEN", "dev")
        return Session(token=dev_token, username="local", role="admin", created_at=0.0, expires_at=1e12, last_activity=time.time())
    
    # Try X-Auth-Token first (session-based auth)
    if x_auth_token:
        session = global_session_store.get(x_auth_token)
        if session:
            return session
        # Token provided but invalid
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")
    
    # Try HTTP Basic Authentication if mode is "basic" or "sessions"
    if authorization and authorization.startswith("Basic "):
        try:
            # Decode Basic auth credentials
            encoded_credentials = authorization.split(" ", 1)[1]
            decoded_credentials = base64.b64decode(encoded_credentials).decode("utf-8")
            username, password = decoded_credentials.split(":", 1)
            
            # Verify credentials
            role = await verify_user(username, password)
            if role:
                # Create an ephemeral session for basic auth (not stored in session store)
                # This allows basic auth to work on every request without session management
                return Session(
                    token=f"basic-{username}",
                    username=username,
                    role=role,
                    created_at=time.time(),
                    expires_at=time.time() + 3600,  # 1 hour
                    last_activity=time.time()
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                    headers={"WWW-Authenticate": "Basic realm=\"HawkFish\""}
                )
        except (ValueError, UnicodeDecodeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Authorization header format",
                headers={"WWW-Authenticate": "Basic realm=\"HawkFish\""}
            )
    
    # No valid authentication provided
    if settings.auth_mode == "basic":
        # For basic auth mode, request basic authentication
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Basic realm=\"HawkFish\""}
        )
    else:
        # For session mode, request token
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Auth-Token or Authorization header"
        )


