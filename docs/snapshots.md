### VM Snapshots & Backups

HawkFish provides comprehensive snapshot management for virtual machines using libvirt's snapshot capabilities.

#### API Endpoints

- `GET /redfish/v1/Systems/{id}/Oem/HawkFish/Snapshots` - List snapshots
- `POST /redfish/v1/Systems/{id}/Oem/HawkFish/Snapshots` - Create snapshot
- `GET /redfish/v1/Systems/{id}/Oem/HawkFish/Snapshots/{snapId}` - Get snapshot details
- `POST /.../Snapshots/{snapId}/Actions/Oem.HawkFish.Snapshot.Revert` - Revert to snapshot
- `DELETE /.../Snapshots/{snapId}` - Delete snapshot

#### Snapshot Schema

```json
{
  "Name": "pre-update-snapshot",
  "Description": "Snapshot before system update"
}
```

#### Features

**Snapshot Types:**
- **External Snapshots**: Uses qcow2 external snapshots when possible
- **Memory State**: Captures both disk and memory state
- **Consistency**: Attempts filesystem quiesce via QEMU Guest Agent

**Lifecycle Management:**
- **Automatic Naming**: Timestamp-based names if not provided
- **State Tracking**: Creating → Ready → Reverting states
- **Background Tasks**: All operations return TaskMonitor for progress
- **Event Integration**: SnapshotCreated/Reverted/Deleted events

**Retention Policy:**
- **Configurable Limits**: Per-system snapshot limits
- **Automatic Cleanup**: Oldest snapshots pruned when limit exceeded
- **Safe Guards**: Referenced snapshots cannot be deleted

#### Consistency & Limitations

**QEMU Guest Agent Integration:**
- **Filesystem Quiesce**: Flushes filesystem caches before snapshot
- **Application Quiesce**: Coordinates with guest applications
- **Fallback**: Proceeds without quiesce if QGA unavailable (with warning)

**Libvirt Compatibility:**
- **Disk Bus Support**: Works with virtio, IDE, SCSI disks
- **Block Device Limitation**: May not support all storage configurations
- **Network Storage**: Limited support for network-backed storage

**Performance Considerations:**
- **External Snapshots**: Minimal performance impact during creation
- **Revert Speed**: Fast revert operations (seconds typically)
- **Storage Overhead**: Snapshots consume additional disk space

#### CLI Usage

```bash
# List snapshots
hawkfish snaps-ls system01

# Create snapshot
hawkfish snaps-create system01 --name "pre-patch" --description "Before security patches"

# Revert to snapshot
hawkfish snaps-revert system01 <snapshot-id>

# Delete snapshot
hawkfish snaps-rm system01 <snapshot-id>
```

#### Error Handling

**Common Issues:**
- **Disk Configuration**: Some disk configurations don't support external snapshots
- **Storage Space**: Insufficient space for snapshot files
- **System State**: Cannot snapshot running systems with certain configurations

**ExtendedInfo Messages:**
- Detailed error information with recommended actions
- Storage requirement estimates
- Configuration compatibility warnings

#### Best Practices

1. **Pre-Change Snapshots**: Always snapshot before major changes
2. **Naming Convention**: Use descriptive names with timestamps
3. **Regular Cleanup**: Monitor snapshot storage usage
4. **Test Reverts**: Verify snapshot integrity periodically
5. **QGA Installation**: Install QEMU Guest Agent for best consistency
