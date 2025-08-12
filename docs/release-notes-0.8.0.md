# HawkFish Release Notes v0.8.0

## Major Features

### 🏢 Multi-Tenancy & Projects
- **Project-based Resource Isolation**: Systems, profiles, images, and volumes are now scoped to projects
- **Quota Management**: Enforce resource limits per project (vCPUs, memory, disk, system count)
- **Role-Based Access Control**: Project members with admin/operator/viewer roles
- **CLI Integration**: Complete project management via `hawkfish projects` commands

### 🔄 Live Migration & Host Maintenance
- **Live System Migration**: Move running VMs between hosts with minimal downtime
- **Host Maintenance Mode**: Automated system evacuation when hosts need maintenance
- **Migration API**: RESTful endpoints for migration operations
- **CLI Support**: `hawkfish migrate` and `hawkfish drain` commands

### 🖥️ Console Access (Framework)
- **WebSocket Console Proxy**: Secure console access with one-time tokens
- **Multi-Protocol Support**: Framework for VNC, SPICE, and serial console access
- **Session Management**: Time-limited console sessions with audit logging
- **Security Model**: Project-scoped access with token-based authentication

### 💾 Storage Pools & Volumes
- **Storage Pool Management**: Support for directory, NFS, LVM, and iSCSI pools
- **Volume Operations**: Create, attach, detach, and resize storage volumes
- **Project Integration**: Volumes are project-scoped with quota enforcement
- **Multiple Formats**: Support for qcow2, raw, and VMDK volume formats

## API Enhancements

### New Endpoints
```
# Projects & Multi-tenancy
GET/POST/DELETE /redfish/v1/Oem/HawkFish/Projects
GET/POST/DELETE /redfish/v1/Oem/HawkFish/Projects/{id}/Members
GET              /redfish/v1/Oem/HawkFish/Projects/{id}/Usage

# Migration & Maintenance  
POST /redfish/v1/Systems/{id}/Actions/Oem.HawkFish.Migrate
POST /redfish/v1/Oem/HawkFish/Hosts/{id}/Actions/EnterMaintenance
POST /redfish/v1/Oem/HawkFish/Hosts/{id}/Actions/ExitMaintenance

# Console Access
POST   /redfish/v1/Systems/{id}/Oem/HawkFish/ConsoleSession
DELETE /redfish/v1/Systems/{id}/Oem/HawkFish/ConsoleSession/{token}
WS     /ws/console/{token}

# Storage Management
GET/POST/DELETE /redfish/v1/Oem/HawkFish/Storage/Pools
GET/POST/DELETE /redfish/v1/Oem/HawkFish/Storage/Volumes
POST            /redfish/v1/Systems/{id}/Oem/HawkFish/Volumes/Attach
POST            /redfish/v1/Systems/{id}/Oem/HawkFish/Volumes/Detach
POST            /redfish/v1/Systems/{id}/Oem/HawkFish/Volumes/{id}/Resize
```

## CLI Enhancements

### New Command Groups
```bash
# Project management
hawkfish projects ls|create|rm
hawkfish projects members|add-member|remove-member

# Migration operations
hawkfish migrate <system> --to <host> [--live|--offline]
hawkfish drain <host>

# Storage management
hawkfish pools ls|create
hawkfish volumes ls|create
```

## Database Schema

### New Tables
- `hf_projects`: Project definitions with quotas
- `hf_project_roles`: Project member roles
- `hf_usage`: Resource usage tracking per project
- `hf_console_sessions`: Console session tokens
- `hf_storage_pools`: Storage pool definitions
- `hf_storage_volumes`: Storage volume metadata
- `hf_volume_attachments`: Volume-to-system mappings

### Schema Migrations
- Added `project_id` columns to existing tables (profiles, images, etc.)
- Automatic migration of existing resources to "default" project

## Events & Monitoring

### New Event Types
- `SystemMigrating` / `SystemMigrated`: Migration lifecycle
- `HostMaintenanceEntered` / `HostMaintenanceExited`: Host maintenance
- `VolumeAttached` / `VolumeDetached` / `VolumeResized`: Storage operations

## Security Enhancements

- **Project-scoped Authorization**: All resource access respects project membership
- **Console Security**: One-time tokens with configurable TTL
- **Quota Enforcement**: Prevents resource exhaustion via quotas

## Configuration Options

### New Environment Variables
```bash
# Console access
HF_CONSOLE_ENABLED=true
HF_CONSOLE_TOKEN_TTL=300
HF_CONSOLE_IDLE_TIMEOUT=600
```

## Breaking Changes

⚠️ **Migration Required**: Existing installations need database migration to add project support. All existing resources will be assigned to the "default" project.

## Deprecations

None in this release.

## Known Limitations

### Console Access
- Console proxy provides framework but requires libvirt graphics integration for production use
- VNC/SPICE protocols need additional WebSocket-to-TCP proxy implementation

### Migration  
- Live migration is currently mock implementation
- Requires shared storage or storage migration capability
- CPU compatibility checking needs libvirt integration

### Storage
- Storage operations are simulated and need libvirt storage pool integration
- Volume resize operations depend on guest OS support for online resize

## Next Release (v0.9.0)

Planned features:
- **OIDC/SSO Integration**: External authentication providers
- **Policy Engine**: OPA-based admission control
- **Real Console Integration**: Working VNC/SPICE proxy
- **Enhanced Migration**: Full libvirt migration implementation

## Upgrade Instructions

1. **Backup Database**: Always backup your HawkFish database before upgrading
2. **Update Configuration**: Review new environment variables
3. **Run Migration**: Database schema will auto-migrate on startup
4. **Update CLI**: Install new CLI version for project management features

## Contributors

This release includes significant architectural enhancements to support enterprise multi-tenancy and advanced VM management capabilities.
