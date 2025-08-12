from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from ..services.console import console_service
from ..services.security import check_project_access, get_current_session
from .errors import redfish_error

router = APIRouter(prefix="/redfish/v1/Systems", tags=["Console"])


class ConsoleSessionCreate(BaseModel):
    protocol: str = "vnc"  # vnc, spice, serial
    duration_seconds: int = 300  # 5 minutes default


@router.post("/{system_id}/Oem/HawkFish/ConsoleSession")
async def create_console_session(
    system_id: str,
    session_data: ConsoleSessionCreate,
    session=Depends(get_current_session),
):
    """Create a console session with one-time token."""
    if not session:
        return redfish_error("AuthenticationRequired", "Authentication required", 401)
    
    user_id = session.get("user_id")
    if not user_id:
        return redfish_error("InvalidSession", "Invalid session", 401)
    
    # Check if user has access to this system (basic check for now)
    # In a full implementation, this would check project membership
    
    try:
        console_session = await console_service.create_session(
            system_id=system_id,
            protocol=session_data.protocol,
            user_id=user_id,
            ttl_seconds=session_data.duration_seconds
        )
        
        # Get connection info
        connection_info = await console_service.get_console_connection_info(
            system_id, session_data.protocol
        )
        
        return {
            "@odata.type": "#ConsoleSession.v1_0_0.ConsoleSession",
            "Id": console_session.token,
            "SystemId": system_id,
            "Protocol": session_data.protocol,
            "WebSocketURL": f"/ws/console/{console_session.token}",
            "ConnectionInfo": connection_info,
            "ExpiresAt": console_session.expires_at,
            "MaxDurationSeconds": session_data.duration_seconds
        }
        
    except ValueError as e:
        return redfish_error("InvalidParameter", str(e), 400)
    except Exception as e:
        return redfish_error("InternalError", str(e), 500)


@router.delete("/{system_id}/Oem/HawkFish/ConsoleSession/{token}")
async def revoke_console_session(
    system_id: str,
    token: str,
    session=Depends(get_current_session),
):
    """Revoke a console session."""
    if not session:
        return redfish_error("AuthenticationRequired", "Authentication required", 401)
    
    # Verify the session belongs to this system and user
    console_session = await console_service.get_session(token)
    if not console_session:
        return redfish_error("ResourceNotFound", "Console session not found", 404)
    
    if console_session.system_id != system_id:
        return redfish_error("InvalidParameter", "Token does not match system", 400)
    
    user_id = session.get("user_id")
    if console_session.user_id != user_id and not session.get("is_admin"):
        return redfish_error("AccessDenied", "Can only revoke your own sessions", 403)
    
    revoked = await console_service.revoke_session(token)
    if not revoked:
        return redfish_error("ResourceNotFound", "Console session not found", 404)
    
    return {"status": "success", "message": "Console session revoked"}


@router.get("/{system_id}/Oem/HawkFish/ConsoleSessions")
async def list_console_sessions(
    system_id: str,
    session=Depends(get_current_session),
):
    """List active console sessions for a system."""
    if not session:
        return redfish_error("AuthenticationRequired", "Authentication required", 401)
    
    sessions = await console_service.list_active_sessions(system_id=system_id)
    
    # Filter to user's own sessions unless admin
    user_id = session.get("user_id")
    if not session.get("is_admin"):
        sessions = [s for s in sessions if s.user_id == user_id]
    
    members = []
    for s in sessions:
        members.append({
            "@odata.id": f"/redfish/v1/Systems/{system_id}/Oem/HawkFish/ConsoleSession/{s.token}",
            "Id": s.token[:8] + "...",  # Truncated for security
            "Protocol": s.protocol,
            "UserId": s.user_id,
            "IsActive": s.is_active,
            "CreatedAt": s.created_at,
            "ExpiresAt": s.expires_at
        })
    
    return {
        "@odata.id": f"/redfish/v1/Systems/{system_id}/Oem/HawkFish/ConsoleSessions",
        "@odata.type": "#ConsoleSessionCollection.ConsoleSessionCollection",
        "Name": "Console Sessions",
        "Members@odata.count": len(members),
        "Members": members
    }


# WebSocket endpoint for console proxy
@router.websocket("/ws/console/{token}")
async def console_websocket(websocket: WebSocket, token: str):
    """WebSocket proxy for console access."""
    await websocket.accept()
    
    try:
        # Validate token
        console_session = await console_service.get_session(token)
        if not console_session:
            await websocket.send_text('{"error": "Invalid or expired token"}')
            await websocket.close(code=4001)
            return
        
        # Activate session (one-time use)
        activated = await console_service.activate_session(token)
        if not activated:
            await websocket.send_text('{"error": "Session already active or expired"}')
            await websocket.close(code=4002)
            return
        
        await websocket.send_text('{"status": "connected", "protocol": "' + console_session.protocol + '"}')
        
        # Get connection info
        connection_info = await console_service.get_console_connection_info(
            console_session.system_id, console_session.protocol
        )
        
        # In a real implementation, this would:
        # 1. Connect to the actual console (VNC/SPICE/serial)
        # 2. Proxy data bidirectionally between WebSocket and console
        # 3. Handle protocol-specific framing
        
        # For now, send mock console data
        await websocket.send_text(f'{{"connection_info": {connection_info}}}')
        await websocket.send_text('{"data": "Mock console output - connected to ' + console_session.system_id + '"}')
        
        # Keep connection alive and handle bidirectional data
        while True:
            try:
                # Wait for client data
                client_data = await websocket.receive_text()
                
                # In real implementation, forward to console
                # For now, echo back
                await websocket.send_text(f'{{"echo": "Received: {client_data}"}}')
                
            except WebSocketDisconnect:
                break
    
    except Exception as e:
        try:
            await websocket.send_text(f'{{"error": "Console proxy error: {str(e)}"}}')
            await websocket.close(code=4000)
        except Exception:
            pass  # Connection might already be closed
    
    finally:
        # Revoke session when WebSocket closes
        await console_service.revoke_session(token)
