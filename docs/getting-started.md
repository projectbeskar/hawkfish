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
