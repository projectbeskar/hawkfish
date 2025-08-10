from fastapi import APIRouter, Header, HTTPException, status

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
def create_session(body: dict):
    username = body.get("UserName", "user")
    session = global_session_store.create_session(username)
    return {
        "Id": session.token,
        "Name": f"Session for {username}",
        "UserName": username,
        "@odata.id": f"/redfish/v1/SessionService/Sessions/{session.token}",
        "X-Auth-Token": session.token,
    }


def require_session(x_auth_token: str | None = Header(default=None, alias="X-Auth-Token")) -> Session:
    if not x_auth_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing X-Auth-Token")
    session = global_session_store.get(x_auth_token)
    if not session:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session token")
    return session


