# Systems Management

This guide covers virtual machine (system) lifecycle management in HawkFish, including creation, power control, configuration, and monitoring.

## Overview

In HawkFish, a "System" represents a virtual machine that can be managed through the Redfish API. Systems are created from profiles and can be assigned to specific projects for multi-tenant isolation.

## Creating Systems

### From Profiles

Systems are typically created from pre-defined profiles that specify resource allocation:

```bash
# List available profiles
hawkfish profiles

# Create a system from a profile
hawkfish systems-create web-server-01 \
  --profile web-small \
  --project production \
  --labels tier=frontend,env=prod
```

#### API Example
```bash
curl -X POST "$HAWKFISH_URL/redfish/v1/Systems" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Name": "web-server-01",
    "ProfileId": "web-small",
    "ProjectId": "production",
    "Oem": {
      "HawkFish": {
        "Labels": {
          "tier": "frontend",
          "environment": "prod"
        }
      }
    }
  }'
```

### Custom Configuration

For ad-hoc systems without profiles:

```bash
hawkfish systems-create test-vm \
  --cpu 2 \
  --memory 4096 \
  --disk 20 \
  --network default \
  --boot-primary hdd
```

### Batch Creation

Create multiple systems efficiently:

```bash
# Create 5 web servers
hawkfish batch-create web-small \
  --count 5 \
  --name-prefix web \
  --start-index 1 \
  --zero-pad 2 \
  --project production
```

## Power Management

### Power States

HawkFish supports standard Redfish power states:

- **Off**: System is powered off
- **On**: System is powered on and running
- **PoweringOn**: System is in the process of powering on
- **PoweringOff**: System is in the process of powering off

### Power Operations

#### Basic Power Control
```bash
# Power on a system
hawkfish power web-01 --action On

# Power off gracefully
hawkfish power web-01 --action GracefulShutdown

# Force power off
hawkfish power web-01 --action ForceOff

# Restart
hawkfish power web-01 --action ForceRestart
```

#### API Power Control
```bash
# Power on via API
curl -X POST "$HAWKFISH_URL/redfish/v1/Systems/web-01/Actions/ComputerSystem.Reset" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ResetType": "On"}'
```

#### Bulk Power Operations
```bash
# Power on all systems with specific labels
hawkfish systems --labels tier=frontend --power-action On

# Emergency shutdown of all systems in a project
hawkfish systems --project test --power-action ForceOff
```

## Boot Configuration

### Boot Sources

HawkFish supports multiple boot sources:

- **Hdd**: Boot from primary disk (default)
- **Cd**: Boot from virtual CD/DVD
- **Pxe**: Network PXE boot
- **Usb**: Boot from virtual USB device

### Boot Override

Set temporary boot override (single boot):

```bash
# Boot from CD once
hawkfish boot web-01 --set cd --once

# Boot from PXE with persistence
hawkfish boot web-01 --set pxe --persist

# Clear boot override
hawkfish boot web-01 --clear
```

#### API Boot Configuration
```bash
curl -X PATCH "$HAWKFISH_URL/redfish/v1/Systems/web-01" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Boot": {
      "BootSourceOverrideTarget": "Cd",
      "BootSourceOverrideEnabled": "Once"
    }
  }'
```

### Boot Order Management

Configure persistent boot order:

```bash
# Set boot order
hawkfish boot web-01 --order "cd,pxe,hdd"

# View current boot configuration
hawkfish systems-show web-01 --detail
```

## Virtual Media Management

### Media Operations

Mount and unmount virtual media (ISO images):

```bash
# List available images
hawkfish images

# Mount an ISO to CD drive
hawkfish media-insert web-01 \
  --image ubuntu-22.04 \
  --device cd

# Eject media
hawkfish media-eject web-01 --device cd

# Check media status
hawkfish media-status web-01
```

#### API Media Operations
```bash
# Insert media
curl -X POST "$HAWKFISH_URL/redfish/v1/Systems/web-01/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Image": "http://images.example.com/ubuntu-22.04.iso",
    "WriteProtected": true
  }'

# Eject media
curl -X POST "$HAWKFISH_URL/redfish/v1/Systems/web-01/VirtualMedia/Cd/Actions/VirtualMedia.EjectMedia" \
  -H "X-Auth-Token: $TOKEN"
```

### Image Management

Add images to the catalog:

```bash
# Add image from URL
hawkfish image-add ubuntu 22.04 \
  --url https://releases.ubuntu.com/22.04/ubuntu-22.04.3-live-server-amd64.iso \
  --sha256 a4acfda10b18da50e2ec50ccaf860d7f20b389df8765611142305c0e911d16fd

# Add local image
hawkfish image-add windows 11 \
  --path /var/lib/hawkfish/isos/windows11.iso \
  --description "Windows 11 Enterprise"
```

## System Information

### Basic Information
```bash
# List all systems
hawkfish systems

# Show system details
hawkfish systems-show web-01

# Filter by labels
hawkfish systems --labels env=prod

# Filter by project
hawkfish systems --project development
```

### Detailed System View
```bash
# Full system details including hardware specs
hawkfish systems-show web-01 --detail

# JSON output for automation
hawkfish systems-show web-01 --format json
```

#### API System Information
```bash
# Get system collection
curl "$HAWKFISH_URL/redfish/v1/Systems" \
  -H "X-Auth-Token: $TOKEN"

# Get specific system
curl "$HAWKFISH_URL/redfish/v1/Systems/web-01" \
  -H "X-Auth-Token: $TOKEN"
```

## System Configuration

### Hardware Configuration

#### CPU Configuration
```bash
# Update CPU count (requires system restart)
hawkfish systems-update web-01 --cpu 4
```

#### Memory Configuration
```bash
# Update memory (requires system restart)
hawkfish systems-update web-01 --memory 8192
```

#### Storage Configuration
```bash
# Add additional disk
hawkfish storage-attach web-01 \
  --size 50 \
  --format qcow2 \
  --name data-disk

# Resize existing disk (requires shutdown)
hawkfish storage-resize web-01 \
  --disk 0 \
  --size 100
```

### Network Configuration

#### Network Interface Management
```bash
# Add network interface
hawkfish network-attach web-01 \
  --network production \
  --mac auto

# Update network configuration
hawkfish network-update web-01 \
  --interface 0 \
  --network dmz
```

### Metadata and Labels

#### System Labels
```bash
# Add labels
hawkfish systems-label web-01 \
  --add tier=frontend \
  --add version=2.1

# Remove labels
hawkfish systems-label web-01 \
  --remove old-label

# Update labels
hawkfish systems-label web-01 \
  --set tier=backend
```

#### System Metadata
```bash
# Update system description
hawkfish systems-update web-01 \
  --description "Production web server - frontend tier"

# Set custom properties
hawkfish systems-update web-01 \
  --custom-property deployment.version=2.1.0 \
  --custom-property maintenance.window=sunday-3am
```

## Console Access

### WebSocket Console

Access system console through WebSocket connection:

```bash
# Open console session
hawkfish console web-01

# Console with specific protocol
hawkfish console web-01 --protocol vnc

# Time-limited console session
hawkfish console web-01 --timeout 3600
```

#### Web UI Console

Access console through the web interface:
1. Navigate to Systems in the Web UI
2. Click on the desired system
3. Click "Open Console"
4. Console opens in new browser tab

### Serial Console

For systems with serial console support:

```bash
# Enable serial console
hawkfish systems-update web-01 --serial-console enabled

# Access serial console
hawkfish console web-01 --type serial
```

## Live Migration

### Migration Operations

Move running systems between hosts:

```bash
# List available hosts
hawkfish hosts

# Migrate system to specific host
hawkfish migrate web-01 --target-host compute-02

# Migrate with storage
hawkfish migrate web-01 \
  --target-host compute-02 \
  --move-storage

# Migration with specific storage pool
hawkfish migrate web-01 \
  --target-host compute-02 \
  --storage-pool fast-ssd
```

#### API Migration
```bash
curl -X POST "$HAWKFISH_URL/redfish/v1/Systems/web-01/Actions/Oem.HawkFish.Migrate" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "TargetHost": "compute-02",
    "MoveStorage": true,
    "StoragePool": "fast-ssd"
  }'
```

### Migration Monitoring

Track migration progress:

```bash
# Watch migration task
hawkfish task-watch <migration-task-id>

# Check system location after migration
hawkfish systems-show web-01 --detail | grep Host
```

## Snapshots and Backup

### Snapshot Management

Create and manage system snapshots:

```bash
# Create snapshot
hawkfish snapshot-create web-01 \
  --name before-update \
  --description "Snapshot before software update"

# List snapshots
hawkfish snapshots web-01

# Restore from snapshot
hawkfish snapshot-restore web-01 \
  --snapshot before-update

# Delete snapshot
hawkfish snapshot-delete web-01 \
  --snapshot before-update
```

### Backup Operations

Full system backup and restore:

```bash
# Backup system (includes config and disks)
hawkfish backup-create web-01 \
  --destination /backup/web-01-$(date +%Y%m%d).tar.gz

# Restore system from backup
hawkfish backup-restore \
  --source /backup/web-01-20241201.tar.gz \
  --name web-01-restored
```

## System Lifecycle

### Complete Lifecycle Example

```bash
# 1. Create system from profile
hawkfish systems-create web-01 --profile web-small

# 2. Configure boot media
hawkfish media-insert web-01 --image ubuntu-22.04

# 3. Set boot order
hawkfish boot web-01 --set cd --once

# 4. Power on system
hawkfish power web-01 --action On

# 5. Monitor installation
hawkfish console web-01

# 6. After installation, remove media
hawkfish media-eject web-01 --device cd

# 7. Restart to boot from disk
hawkfish power web-01 --action ForceRestart

# 8. Verify system is running
hawkfish systems-show web-01
```

### System Deletion

```bash
# Graceful shutdown and delete
hawkfish power web-01 --action GracefulShutdown
hawkfish systems-delete web-01

# Force delete (with confirmation)
hawkfish systems-delete web-01 --force

# Delete with cleanup
hawkfish systems-delete web-01 --cleanup-storage
```

## Troubleshooting

### Common Issues

#### System Won't Start
```bash
# Check system configuration
hawkfish systems-show web-01 --detail

# Check host capacity
hawkfish hosts

# Check recent tasks
hawkfish tasks --system web-01 --recent
```

#### Boot Problems
```bash
# Check boot configuration
hawkfish systems-show web-01 | grep Boot

# Verify media status
hawkfish media-status web-01

# Reset boot configuration
hawkfish boot web-01 --clear
```

#### Performance Issues
```bash
# Check system resource allocation
hawkfish systems-show web-01 --detail | grep -E "(CPU|Memory|Storage)"

# Check host performance
hawkfish hosts --detail

# Monitor system metrics
hawkfish metrics web-01
```

### Debug Mode

Enable detailed logging for troubleshooting:

```bash
# Start with debug logging
HF_LOG_LEVEL=DEBUG hawkfish-controller

# Check specific operations
hawkfish --debug systems-create test-debug --profile small
```

### Support Information

For additional support:
- Check the [Operations Guide](ops.md) for maintenance procedures
- Review [Event logs](events.md) for system activity
- Consult [Performance tuning](scale-performance.md) for optimization
- See [Troubleshooting Guide](troubleshooting.md) for common solutions
