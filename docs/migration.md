# Live Migration & Host Maintenance

HawkFish supports live migration of systems between hosts and automated host maintenance workflows.

## Live Migration

Move running systems between hosts with minimal downtime.

### API Endpoints

```
POST /redfish/v1/Systems/{systemId}/Actions/Oem.HawkFish.Migrate
```

**Request Body:**
```json
{
  "TargetHostId": "host-02",
  "LiveMigration": true
}
```

### CLI Commands

```bash
# Live migrate system to another host
hawkfish migrate node-01 --to host-02 --live

# Offline migration
hawkfish migrate node-01 --to host-02 --offline
```

## Host Maintenance

Put hosts into maintenance mode with automatic system evacuation.

### API Endpoints

```
POST /redfish/v1/Oem/HawkFish/Hosts/{hostId}/Actions/EnterMaintenance
POST /redfish/v1/Oem/HawkFish/Hosts/{hostId}/Actions/ExitMaintenance
```

### CLI Commands

```bash
# Enter maintenance mode (evacuates all systems)
hawkfish drain host-01

# Exit maintenance mode
hawkfish hosts exit-maintenance host-01
```

## Migration Process

1. **Pre-checks**: CPU compatibility, shared storage availability
2. **Preparation**: Memory pre-copy, disk synchronization
3. **Cutover**: Brief pause, final state transfer
4. **Completion**: Update host assignments, emit events

## Requirements

- **Shared Storage**: Systems must use shared storage or storage migration
- **CPU Compatibility**: Source and target hosts need compatible CPU features
- **Network**: High-bandwidth connection between hosts recommended

## Events

Migration operations emit events for monitoring:

- `SystemMigrating`: Migration started
- `SystemMigrated`: Migration completed
- `HostMaintenanceEntered`: Host entered maintenance mode
- `HostMaintenanceExited`: Host exited maintenance mode

## Scheduler Integration

The scheduler automatically avoids hosts in maintenance mode when placing new systems.
