# Console Access

HawkFish provides secure console access to systems via WebSocket proxy with one-time tokens.

## Supported Protocols

- **VNC**: Virtual Network Computing for graphical console
- **SPICE**: Simple Protocol for Independent Computing Environments
- **Serial**: Text-based serial console

## API Endpoints

```
POST   /redfish/v1/Systems/{systemId}/Oem/HawkFish/ConsoleSession
DELETE /redfish/v1/Systems/{systemId}/Oem/HawkFish/ConsoleSession/{token}
GET    /redfish/v1/Systems/{systemId}/Oem/HawkFish/ConsoleSessions

# WebSocket endpoint
WS /ws/console/{token}
```

## Creating Console Sessions

### Request

```bash
curl -X POST /redfish/v1/Systems/node-01/Oem/HawkFish/ConsoleSession \
  -H "Content-Type: application/json" \
  -d '{
    "protocol": "vnc",
    "duration_seconds": 300
  }'
```

### Response

```json
{
  "@odata.type": "#ConsoleSession.v1_0_0.ConsoleSession",
  "Id": "abc123def456",
  "SystemId": "node-01", 
  "Protocol": "vnc",
  "WebSocketURL": "/ws/console/abc123def456",
  "ConnectionInfo": {
    "host": "localhost",
    "port": 5900,
    "protocol": "vnc",
    "display": ":0"
  },
  "ExpiresAt": 1645123456.789,
  "MaxDurationSeconds": 300
}
```

## WebSocket Protocol

Connect to the WebSocket URL with the one-time token:

```javascript
const ws = new WebSocket('wss://hawkfish.example.com/ws/console/abc123def456');

ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Console data:', data);
};

ws.send(JSON.stringify({type: 'input', data: 'ls\n'}));
```

## Security Features

- **One-time tokens**: Tokens are single-use and expire quickly
- **Time-limited**: Configurable session duration (default 5 minutes)
- **Project-scoped**: Users can only access systems in their projects
- **Audit logging**: All console access is logged

## Configuration

```bash
export HF_CONSOLE_ENABLED=true
export HF_CONSOLE_TOKEN_TTL=300      # 5 minutes
export HF_CONSOLE_IDLE_TIMEOUT=600   # 10 minutes
```

## Integration with UI

The HawkFish UI provides a console panel that:

1. Creates console sessions via API
2. Opens WebSocket connection with token
3. Renders console output (VNC via noVNC, serial via xterm.js)
4. Handles user input and connection lifecycle

## Limitations

- **Mock Implementation**: Current implementation provides framework with mock console data
- **Real Integration**: Production requires integration with libvirt graphics configuration
- **Protocol Support**: Actual VNC/SPICE proxy implementation needed for graphics protocols
