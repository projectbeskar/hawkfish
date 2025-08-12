# Storage Pools & Volumes

HawkFish provides comprehensive storage management with pools and volumes for virtual machine storage.

## Storage Pools

Storage pools define storage backends for creating volumes.

### Supported Pool Types

- **dir**: Directory-based storage (default)
- **nfs**: Network File System storage
- **lvm**: Logical Volume Manager
- **iscsi**: iSCSI storage

### API Endpoints

```
GET    /redfish/v1/Oem/HawkFish/Storage/Pools
POST   /redfish/v1/Oem/HawkFish/Storage/Pools
GET    /redfish/v1/Oem/HawkFish/Storage/Pools/{poolId}
DELETE /redfish/v1/Oem/HawkFish/Storage/Pools/{poolId}
```

### CLI Commands

```bash
# List storage pools
hawkfish pools ls

# Create directory pool
hawkfish pools create mypool --type dir --path /var/lib/hawkfish/storage --host host-01 --capacity 500

# Create NFS pool
hawkfish pools create nfspool --type nfs --path server:/exports/vms --host host-01 --capacity 1000
```

## Storage Volumes

Volumes are individual storage units created from pools.

### Supported Formats

- **qcow2**: QEMU Copy On Write (default, supports snapshots)
- **raw**: Raw disk image (better performance)
- **vmdk**: VMware Virtual Machine Disk

### API Endpoints

```
GET    /redfish/v1/Oem/HawkFish/Storage/Volumes
POST   /redfish/v1/Oem/HawkFish/Storage/Volumes
GET    /redfish/v1/Oem/HawkFish/Storage/Volumes/{volumeId}
DELETE /redfish/v1/Oem/HawkFish/Storage/Volumes/{volumeId}
```

### CLI Commands

```bash
# List volumes
hawkfish volumes ls

# Filter by pool or project
hawkfish volumes ls --pool mypool --project development

# Create volume
hawkfish volumes create data-disk --pool mypool --capacity 50 --format qcow2 --project development
```

## Volume Operations

### Attach/Detach

```bash
# API
POST /redfish/v1/Systems/{systemId}/Oem/HawkFish/Volumes/Attach
POST /redfish/v1/Systems/{systemId}/Oem/HawkFish/Volumes/Detach

# Request body for attach
{
  "volume_id": "vol-123",
  "device": "vdb"
}
```

### Resize

```bash
# API
POST /redfish/v1/Systems/{systemId}/Oem/HawkFish/Volumes/{volumeId}/Resize

# Request body
{
  "capacity_gb": 100
}
```

## Project Integration

Volumes belong to projects and are subject to project quotas:

- **Disk Quota**: Total volume capacity counts against project disk quota
- **Access Control**: Users can only manage volumes in their accessible projects
- **Isolation**: Projects cannot access other projects' volumes

## Capacity Management

Storage pools track capacity utilization:

- **Total Capacity**: Maximum storage available in the pool
- **Allocated**: Storage reserved by volumes (may be thin-provisioned)
- **Available**: Remaining capacity for new volumes

## Events

Storage operations emit events:

- `VolumeAttached`: Volume attached to system
- `VolumeDetached`: Volume detached from system  
- `VolumeResized`: Volume capacity increased

## Integration with Node Creation

Storage volumes can be specified in node profiles and batch operations:

```json
{
  "name": "web-server-profile",
  "cpu": 2,
  "memory_mib": 4096,
  "disk_gib": 20,
  "additional_volumes": [
    {
      "name": "data-volume",
      "capacity_gb": 100,
      "pool_id": "data-pool",
      "device": "vdb"
    }
  ]
}
```

## Limitations

- **Mock Implementation**: Current storage operations are simulated
- **Real Integration**: Production requires libvirt storage pool management
- **Live Resize**: Online volume resize depends on guest OS support
