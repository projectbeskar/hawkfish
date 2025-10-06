# Getting Started with HawkFish

This guide will help you quickly connect HawkFish to a libvirt host and start managing virtual machines through the Redfish API.

## Quick Start

### Prerequisites

1. **Python 3.11+** installed
2. **Libvirt host** accessible (local or remote)
3. **HawkFish** installed: `pip install hawkfish`

### Step 1: Verify Libvirt Access

First, ensure you can connect to your libvirt host:

#### Local libvirt (same machine)
```bash
# Check libvirt is running
sudo systemctl status libvirtd

# Add your user to libvirt group (if needed)
sudo usermod -a -G libvirt $USER
# Log out and back in for group changes to take effect

# Test connection
virsh -c qemu:///system list --all
```

#### Remote libvirt (SSH)
```bash
# Test SSH connection to remote host
ssh user@remote-host virsh list --all

# Ensure SSH keys are set up for passwordless authentication
ssh-copy-id user@remote-host
```

### Step 2: Start HawkFish Controller

#### Option A: Local Libvirt

```bash
# Set the libvirt URI to local system
export LIBVIRT_URI="qemu:///system"

# Basic configuration
export HF_API_HOST="0.0.0.0"
export HF_API_PORT="8080"
export HF_AUTH="none"           # Disable auth for testing
export HF_UI_ENABLED="true"     # Enable web UI

# Start the controller
hawkfish-controller
```

#### Option B: Remote Libvirt (SSH)

```bash
# Set the libvirt URI to remote host via SSH
export LIBVIRT_URI="qemu+ssh://user@remote-host/system"

# Basic configuration
export HF_API_HOST="0.0.0.0"
export HF_API_PORT="8080"
export HF_AUTH="none"           # Disable auth for testing
export HF_UI_ENABLED="true"     # Enable web UI

# Start the controller
hawkfish-controller
```

#### Option C: Remote Libvirt (TLS)

```bash
# Set the libvirt URI to remote host via TLS
export LIBVIRT_URI="qemu+tls://remote-host/system"

# Basic configuration
export HF_API_HOST="0.0.0.0"
export HF_API_PORT="8080"
export HF_AUTH="none"
export HF_UI_ENABLED="true"

# Start the controller
hawkfish-controller
```

#### Option D: Using Configuration File

Create `hawkfish.toml`:

```toml
[api]
host = "0.0.0.0"
port = 8080

[auth]
mode = "none"  # Use "sessions" for production

[ui]
enabled = true

[libvirt]
# Choose one:
uri = "qemu:///system"                          # Local
# uri = "qemu+ssh://user@remote-host/system"   # Remote SSH
# uri = "qemu+tls://remote-host/system"        # Remote TLS

[libvirt.pool]
min = 1
max = 10
ttl_sec = 300

[storage]
state_dir = "/var/lib/hawkfish"
iso_dir = "/var/lib/hawkfish/isos"
```

Then start:
```bash
hawkfish-controller --config hawkfish.toml
```

### Step 3: Test the Connection

Once HawkFish is running, you should see output like:

```
INFO:     Starting HawkFish Controller v0.1.0
INFO:     Libvirt URI: qemu:///system
INFO:     API listening on http://0.0.0.0:8080
INFO:     Docs available at http://0.0.0.0:8080/docs
INFO:     UI available at http://0.0.0.0:8080/ui/
```

#### Test API Access

```bash
# Check service root
curl http://localhost:8080/redfish/v1/

# List systems (VMs)
curl http://localhost:8080/redfish/v1/Systems

# Get system details
curl http://localhost:8080/redfish/v1/Systems/{system-id}
```

#### Access Web UI

Open your browser to: `http://localhost:8080/ui/`

#### Access API Documentation

Open your browser to: `http://localhost:8080/docs`

## Authentication

HawkFish supports multiple authentication modes. For testing, you can disable authentication, but **always use authentication in production**.

### Authentication Modes

HawkFish supports three authentication modes:

1. **`none`** - No authentication (development/testing only)
2. **`sessions`** - Token-based session authentication (recommended for production)
3. **`basic`** - HTTP Basic authentication

### Option 1: No Authentication (Testing Only)

```bash
export HF_AUTH="none"
hawkfish-controller

# Access API without authentication
curl http://localhost:8080/redfish/v1/Systems
```

**Warning**: Only use this in trusted development environments.

### Option 2: Session-Based Authentication (Recommended)

Session-based authentication uses tokens for secure API access.

#### Start HawkFish with Authentication

```bash
# Enable session authentication
export LIBVIRT_URI="qemu:///system"
export HF_API_HOST="0.0.0.0"
export HF_API_PORT="8080"
export HF_AUTH="sessions"
export HF_UI_ENABLED="true"

# Start the controller
hawkfish-controller
```

#### Create a User Session

First, authenticate to get a session token:

```bash
# Login to create a session
curl -X POST http://localhost:8080/redfish/v1/SessionService/Sessions \
  -H "Content-Type: application/json" \
  -d '{
    "UserName": "admin",
    "Password": "admin"
  }'
```

**Response:**
```json
{
  "@odata.type": "#Session.v1_0_0.Session",
  "Id": "1234567890",
  "Name": "User Session",
  "UserName": "admin",
  "Token": "abc123def456ghi789jkl012mno345pqr678",
  "@odata.id": "/redfish/v1/SessionService/Sessions/1234567890"
}
```

#### Use the Session Token

Include the token in the `X-Auth-Token` header for all API requests:

```bash
# Save the token
TOKEN="abc123def456ghi789jkl012mno345pqr678"

# Use the token for authenticated requests
curl http://localhost:8080/redfish/v1/Systems \
  -H "X-Auth-Token: $TOKEN"

# Power on a system
curl -X POST http://localhost:8080/redfish/v1/Systems/test-vm/Actions/ComputerSystem.Reset \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ResetType": "On"}'

# Create a new system
curl -X POST http://localhost:8080/redfish/v1/Systems \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Name": "authenticated-vm",
    "Memory": 2048,
    "ProcessorCount": 2,
    "DiskSize": 20480
  }'
```

#### Delete the Session (Logout)

When you're done, delete the session. The session ID is returned when you create the session:

```bash
# When logging in, capture both the token AND session ID
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8080/redfish/v1/SessionService/Sessions \
  -H "Content-Type: application/json" \
  -d '{"UserName": "admin", "Password": "admin"}')

# Extract both values
TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.Token')
SESSION_ID=$(echo $LOGIN_RESPONSE | jq -r '.Id')

# Later, delete the session using both
curl -X DELETE http://localhost:8080/redfish/v1/SessionService/Sessions/$SESSION_ID \
  -H "X-Auth-Token: $TOKEN"
```

**Tip**: If you lost your session ID, you can list all sessions:

```bash
# List all active sessions
curl http://localhost:8080/redfish/v1/SessionService/Sessions \
  -H "X-Auth-Token: $TOKEN"
```

### Option 3: Basic Authentication

HTTP Basic authentication sends credentials with each request.

#### Start HawkFish with Basic Auth

```bash
export HF_AUTH="basic"
hawkfish-controller
```

#### Use Basic Authentication

```bash
# Include credentials in each request
curl -u admin:admin http://localhost:8080/redfish/v1/Systems

# Or use base64 encoded credentials
curl -H "Authorization: Basic YWRtaW46YWRtaW4=" \
  http://localhost:8080/redfish/v1/Systems
```

### Complete Authentication Example

Here's a complete workflow with authentication:

```bash
# 1. Start HawkFish with authentication enabled
export LIBVIRT_URI="qemu:///system"
export HF_AUTH="sessions"
export HF_API_HOST="0.0.0.0"
export HF_API_PORT="8080"
hawkfish-controller &

# Wait for startup
sleep 3

# 2. Login and get session token
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8080/redfish/v1/SessionService/Sessions \
  -H "Content-Type: application/json" \
  -d '{"UserName": "admin", "Password": "admin"}')

# 3. Extract token from response
TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"Token":"[^"]*"' | cut -d'"' -f4)
echo "Session Token: $TOKEN"

# 4. Use the token for API operations
echo "Listing systems..."
curl -s http://localhost:8080/redfish/v1/Systems \
  -H "X-Auth-Token: $TOKEN" | jq .

# 5. Get system details
echo "Getting system details..."
curl -s http://localhost:8080/redfish/v1/Systems/my-vm \
  -H "X-Auth-Token: $TOKEN" | jq .

# 6. Power on a system
echo "Powering on system..."
curl -X POST http://localhost:8080/redfish/v1/Systems/my-vm/Actions/ComputerSystem.Reset \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ResetType": "On"}'

# 7. Logout (delete session)
SESSION_ID=$(echo $LOGIN_RESPONSE | grep -o '"Id":"[^"]*"' | cut -d'"' -f4)
curl -X DELETE http://localhost:8080/redfish/v1/SessionService/Sessions/$SESSION_ID \
  -H "X-Auth-Token: $TOKEN"

echo "Session terminated"
```

### Python Example with Authentication

Here's a Python example using the session API:

```python
import requests
import json

# HawkFish API endpoint
BASE_URL = "http://localhost:8080"

class HawkFishClient:
    def __init__(self, base_url, username="admin", password="admin"):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.session_token = None
        self.session_id = None
    
    def login(self):
        """Create a session and get authentication token."""
        url = f"{self.base_url}/redfish/v1/SessionService/Sessions"
        payload = {
            "UserName": self.username,
            "Password": self.password
        }
        
        response = requests.post(url, json=payload)
        response.raise_for_status()
        
        data = response.json()
        self.session_token = data["Token"]
        self.session_id = data["Id"]
        
        print(f"Logged in successfully. Session ID: {self.session_id}")
        return self.session_token
    
    def logout(self):
        """Delete the session."""
        if not self.session_token or not self.session_id:
            return
        
        url = f"{self.base_url}/redfish/v1/SessionService/Sessions/{self.session_id}"
        headers = {"X-Auth-Token": self.session_token}
        
        response = requests.delete(url, headers=headers)
        response.raise_for_status()
        
        print("Logged out successfully")
        self.session_token = None
        self.session_id = None
    
    def get_headers(self):
        """Get headers with authentication token."""
        if not self.session_token:
            raise ValueError("Not authenticated. Call login() first.")
        return {"X-Auth-Token": self.session_token}
    
    def list_systems(self):
        """List all systems."""
        url = f"{self.base_url}/redfish/v1/Systems"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()
    
    def get_system(self, system_id):
        """Get details of a specific system."""
        url = f"{self.base_url}/redfish/v1/Systems/{system_id}"
        response = requests.get(url, headers=self.get_headers())
        response.raise_for_status()
        return response.json()
    
    def power_on(self, system_id):
        """Power on a system."""
        url = f"{self.base_url}/redfish/v1/Systems/{system_id}/Actions/ComputerSystem.Reset"
        payload = {"ResetType": "On"}
        response = requests.post(url, json=payload, headers=self.get_headers())
        response.raise_for_status()
        return response.json()
    
    def create_system(self, name, memory_mb, cpu_count, disk_gb):
        """Create a new system."""
        url = f"{self.base_url}/redfish/v1/Systems"
        payload = {
            "Name": name,
            "Memory": memory_mb,
            "ProcessorCount": cpu_count,
            "DiskSize": disk_gb * 1024  # Convert to MB
        }
        response = requests.post(url, json=payload, headers=self.get_headers())
        response.raise_for_status()
        return response.json()

# Usage example
if __name__ == "__main__":
    client = HawkFishClient("http://localhost:8080", "admin", "admin")
    
    try:
        # Login
        client.login()
        
        # List systems
        systems = client.list_systems()
        print(f"Found {systems['Members@odata.count']} systems")
        
        # Get details of first system
        if systems["Members"]:
            system_url = systems["Members"][0]["@odata.id"]
            system_id = system_url.split("/")[-1]
            
            system_details = client.get_system(system_id)
            print(f"System: {system_details['Name']}")
            print(f"Power State: {system_details['PowerState']}")
            print(f"Memory: {system_details['MemorySummary']['TotalSystemMemoryGiB']} GiB")
        
        # Create a new system
        new_system = client.create_system(
            name="authenticated-vm",
            memory_mb=4096,
            cpu_count=4,
            disk_gb=50
        )
        print(f"Created system: {new_system['Name']}")
        
    finally:
        # Always logout
        client.logout()
```

### Authentication with Web UI

When using the web UI with authentication enabled:

1. Navigate to `http://localhost:8080/ui/`
2. You'll see a login page
3. Enter credentials (default: `admin` / `admin`)
4. The UI will automatically handle session token management

### Default Credentials

The default credentials for HawkFish are:

- **Username**: `admin`
- **Password**: `admin`

**Important**: Change these credentials in production environments.

### Managing Users

User management in HawkFish is handled through the configuration or external authentication systems. For the built-in authentication:

```bash
# Configure custom credentials via environment variables
export HF_ADMIN_USERNAME="myadmin"
export HF_ADMIN_PASSWORD="secure-password-here"
export HF_AUTH="sessions"

hawkfish-controller
```

### Authentication Best Practices

1. **Never use `none` auth in production**
2. **Always use TLS/HTTPS** with authentication
3. **Rotate session tokens regularly** (sessions expire after inactivity)
4. **Use strong passwords** for the admin account
5. **Delete sessions when done** (logout properly)
6. **Monitor authentication failures** via audit logs
7. **Use environment-specific credentials** (don't hardcode)

### Troubleshooting Authentication

#### Problem: How do I find my session ID?

The session ID is returned in the login response. Always save it:

**Best Practice:**
```bash
# Save the entire login response
LOGIN_RESPONSE=$(curl -s -X POST http://localhost:8080/redfish/v1/SessionService/Sessions \
  -H "Content-Type: application/json" \
  -d '{"UserName": "admin", "Password": "admin"}')

# Parse out what you need
TOKEN=$(echo $LOGIN_RESPONSE | jq -r '.Token')
SESSION_ID=$(echo $LOGIN_RESPONSE | jq -r '.Id')

# Store them for later use
echo "TOKEN=$TOKEN" > .hawkfish_session
echo "SESSION_ID=$SESSION_ID" >> .hawkfish_session
```

**If you lost the session ID:**

Option 1 - List all sessions:
```bash
curl http://localhost:8080/redfish/v1/SessionService/Sessions \
  -H "X-Auth-Token: $TOKEN" | jq .
```

Option 2 - Extract from the @odata.id in the login response:
```bash
# The session ID is the last part of the @odata.id
SESSION_ID=$(echo $LOGIN_RESPONSE | jq -r '.["@odata.id"]' | awk -F'/' '{print $NF}')
```

Option 3 - Look at the Location header:
```bash
# Use -i to see headers
curl -i -X POST http://localhost:8080/redfish/v1/SessionService/Sessions \
  -H "Content-Type: application/json" \
  -d '{"UserName": "admin", "Password": "admin"}' | grep Location
# Location: /redfish/v1/SessionService/Sessions/SESSION_ID_HERE
```

#### Problem: 401 Unauthorized

```
{"error": "@Message.ExtendedInfo": [...], "code": 401}
```

**Solutions:**

1. Ensure you're including the `X-Auth-Token` header
2. Verify the token is valid (not expired)
3. Check you logged in successfully

#### Problem: Token Expired

Sessions expire after a period of inactivity (default: 30 minutes).

**Solution**: Login again to get a new token:

```bash
# Get a new session token
curl -X POST http://localhost:8080/redfish/v1/SessionService/Sessions \
  -H "Content-Type: application/json" \
  -d '{"UserName": "admin", "Password": "admin"}'
```

#### Problem: Invalid Credentials

```
{"error": "Invalid credentials"}
```

**Solutions:**

1. Verify username and password are correct
2. Check if you're using the configured credentials
3. Ensure authentication mode is set correctly

## Common Libvirt URI Formats

HawkFish supports all standard libvirt URIs:

### Local Connections
```bash
# Local system QEMU/KVM
LIBVIRT_URI="qemu:///system"

# Local session (user-level VMs)
LIBVIRT_URI="qemu:///session"
```

### Remote Connections via SSH
```bash
# Basic SSH connection
LIBVIRT_URI="qemu+ssh://user@host/system"

# SSH with custom port
LIBVIRT_URI="qemu+ssh://user@host:2222/system"

# SSH with keyfile specification (requires SSH config)
LIBVIRT_URI="qemu+ssh://user@host/system"
# Add to ~/.ssh/config:
#   Host host
#     IdentityFile ~/.ssh/custom_key
```

### Remote Connections via TLS
```bash
# TLS connection (requires certificates)
LIBVIRT_URI="qemu+tls://host/system"
```

### Remote Connections via TCP (not recommended for production)
```bash
# TCP connection (no encryption - use for testing only)
LIBVIRT_URI="qemu+tcp://host/system"
```

## Working with Multiple Hosts

HawkFish supports connecting to multiple libvirt hosts simultaneously. There are two approaches:

### Approach 1: Default Host (Simple)

Set a single default host via `LIBVIRT_URI`:

```bash
export LIBVIRT_URI="qemu+ssh://host1/system"
hawkfish-controller
```

All API operations will use this host by default.

### Approach 2: Multiple Hosts (Advanced)

Register multiple hosts via the API after starting HawkFish:

```bash
# Start with a default host
export LIBVIRT_URI="qemu:///system"
hawkfish-controller &

# Add additional hosts via API
curl -X POST http://localhost:8080/redfish/v1/Oem/HawkFish/Hosts \
  -H "Content-Type: application/json" \
  -d '{
    "URI": "qemu+ssh://host1/system",
    "Name": "host1",
    "Labels": {"region": "us-west", "env": "production"}
  }'

curl -X POST http://localhost:8080/redfish/v1/Oem/HawkFish/Hosts \
  -H "Content-Type: application/json" \
  -d '{
    "URI": "qemu+ssh://host2/system",
    "Name": "host2",
    "Labels": {"region": "us-east", "env": "production"}
  }'

# List registered hosts
curl http://localhost:8080/redfish/v1/Oem/HawkFish/Hosts

# Systems will now show VMs from all registered hosts
curl http://localhost:8080/redfish/v1/Systems
```

## Example: Complete Workflow

Here's a complete example of starting HawkFish and testing it:

```bash
# 1. Set up environment
export LIBVIRT_URI="qemu:///system"
export HF_API_HOST="0.0.0.0"
export HF_API_PORT="8080"
export HF_AUTH="none"
export HF_UI_ENABLED="true"

# 2. Start HawkFish
hawkfish-controller

# In another terminal:

# 3. Check HawkFish is running
curl http://localhost:8080/redfish/v1/

# 4. List existing VMs
curl http://localhost:8080/redfish/v1/Systems

# 5. Create a new VM from a profile
curl -X POST http://localhost:8080/redfish/v1/Systems \
  -H "Content-Type: application/json" \
  -d '{
    "Name": "test-vm",
    "Memory": 2048,
    "ProcessorCount": 2,
    "DiskSize": 20480
  }'

# 6. Power on the VM
curl -X POST http://localhost:8080/redfish/v1/Systems/test-vm/Actions/ComputerSystem.Reset \
  -H "Content-Type: application/json" \
  -d '{"ResetType": "On"}'

# 7. Check VM status
curl http://localhost:8080/redfish/v1/Systems/test-vm
```

## Troubleshooting

### Connection Issues

#### Problem: Cannot connect to libvirt
```
Error: Failed to get connection to libvirt at qemu:///system
```

**Solutions:**

1. Check libvirt is running:
   ```bash
   sudo systemctl status libvirtd
   sudo systemctl start libvirtd
   ```

2. Check permissions:
   ```bash
   sudo usermod -a -G libvirt $USER
   # Log out and back in
   groups  # Verify libvirt group is present
   ```

3. Test manually:
   ```bash
   virsh -c qemu:///system list --all
   ```

#### Problem: Cannot connect to remote libvirt via SSH
```
Error: Failed to get connection to libvirt at qemu+ssh://user@host/system
```

**Solutions:**

1. Test SSH access:
   ```bash
   ssh user@host virsh list --all
   ```

2. Set up SSH keys:
   ```bash
   ssh-copy-id user@host
   ```

3. Verify SSH config allows agent forwarding if needed

#### Problem: Permission denied on remote host
```
Error: authentication failed
```

**Solutions:**

1. On remote host, add user to libvirt group:
   ```bash
   sudo usermod -a -G libvirt username
   ```

2. Verify remote libvirt is configured to allow your user

### Performance Issues

#### Problem: Slow responses

**Solutions:**

1. Increase connection pool size:
   ```bash
   export HF_LIBVIRT_POOL_MIN=2
   export HF_LIBVIRT_POOL_MAX=20
   ```

2. Reduce TTL if connections are timing out:
   ```bash
   export HF_LIBVIRT_POOL_TTL_SEC=180
   ```

### Debug Mode

Enable debug logging to troubleshoot issues:

```bash
export HF_LOG_LEVEL="DEBUG"
hawkfish-controller
```

## Next Steps

- **[API Documentation](api.md)**: Learn about all available Redfish endpoints
- **[Architecture](architecture.md)**: Understand how HawkFish works
- **[Deployment Guide](deploy.md)**: Production deployment options
- **[Operations Guide](ops.md)**: Day-to-day operations and management
- **[Examples](../examples/)**: More code examples and use cases

## Common Use Cases

### Development Environment

```bash
# Simple local setup for testing
export LIBVIRT_URI="qemu:///system"
export HF_AUTH="none"
export HF_UI_ENABLED="true"
hawkfish-controller --host 0.0.0.0 --port 8080
```

### Production Environment

```toml
# hawkfish-prod.toml
[api]
host = "0.0.0.0"
port = 8443

[auth]
mode = "sessions"

[tls]
mode = "custom"
cert = "/etc/hawkfish/certs/server.crt"
key = "/etc/hawkfish/certs/server.key"

[libvirt]
uri = "qemu+ssh://admin@hypervisor/system"

[libvirt.pool]
min = 5
max = 50
ttl_sec = 600
```

```bash
hawkfish-controller --config hawkfish-prod.toml
```

### Multi-Region Setup

```bash
# Start controller
export LIBVIRT_URI="qemu:///system"  # Default/management host
hawkfish-controller &

# Register regional hosts
curl -X POST http://localhost:8080/redfish/v1/Oem/HawkFish/Hosts \
  -H "Content-Type: application/json" \
  -d '{"URI": "qemu+ssh://us-west-1/system", "Name": "us-west-1", "Labels": {"region": "us-west"}}'

curl -X POST http://localhost:8080/redfish/v1/Oem/HawkFish/Hosts \
  -H "Content-Type: application/json" \
  -d '{"URI": "qemu+ssh://us-east-1/system", "Name": "us-east-1", "Labels": {"region": "us-east"}}'

curl -X POST http://localhost:8080/redfish/v1/Oem/HawkFish/Hosts \
  -H "Content-Type: application/json" \
  -d '{"URI": "qemu+ssh://eu-central-1/system", "Name": "eu-central-1", "Labels": {"region": "eu-central"}}'
```

## Security Considerations

### For Testing/Development

- Use `HF_AUTH="none"` to disable authentication
- Use `HF_DEV_TLS="off"` for HTTP (no TLS)
- Use local or trusted network only

### For Production

- **Always** use `HF_AUTH="sessions"` or `HF_AUTH="basic"`
- **Always** use TLS (`HF_DEV_TLS="self-signed"` or custom certificates)
- Use strong authentication on libvirt hosts
- Use SSH keys for remote connections
- Implement network segmentation and firewalls
- Regular security audits

## Getting Help

- **Documentation**: Check the [docs/](../docs/) directory
- **Examples**: See [examples/](../examples/) for working code
- **API Docs**: Visit `/docs` endpoint while running
- **Issues**: Report bugs on GitHub Issues
- **Discussions**: Ask questions on GitHub Discussions
