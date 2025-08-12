# Multi-Tenancy

HawkFish v0.8.0+ supports multi-tenant projects with quota enforcement and role-based access control.

## Projects

Projects provide resource isolation and quota management. Each project has:

- **Resource Quotas**: vCPUs, memory (GiB), disk (GiB), system count
- **Members**: Users with roles (admin, operator, viewer)
- **Scoped Resources**: Systems, profiles, images, volumes belong to projects

### API Endpoints

```
GET    /redfish/v1/Oem/HawkFish/Projects
POST   /redfish/v1/Oem/HawkFish/Projects
GET    /redfish/v1/Oem/HawkFish/Projects/{id}
DELETE /redfish/v1/Oem/HawkFish/Projects/{id}

GET    /redfish/v1/Oem/HawkFish/Projects/{id}/Members
POST   /redfish/v1/Oem/HawkFish/Projects/{id}/Members
DELETE /redfish/v1/Oem/HawkFish/Projects/{id}/Members/{userId}

GET    /redfish/v1/Oem/HawkFish/Projects/{id}/Usage
POST   /redfish/v1/Oem/HawkFish/Projects/{id}/Actions/SetQuotas
```

### CLI Commands

```bash
# List projects
hawkfish projects ls

# Create project
hawkfish projects create "MyProject" --description "Development project" --vcpus 50

# Manage members
hawkfish projects add-member myproject user123 --role operator
hawkfish projects members myproject
hawkfish projects remove-member myproject user123
```

## Quotas

Resource quotas are enforced during node creation:

- **vCPUs**: Total virtual CPUs across all systems
- **Memory**: Total memory in GiB across all systems  
- **Disk**: Total disk space in GiB across all systems
- **Systems**: Maximum number of systems

Quota violations return Redfish error responses with `ExtendedInfo`.

## Role-Based Access Control

### Roles

- **admin**: Full project management, member management, resource operations
- **operator**: Resource operations (create/modify/delete systems)
- **viewer**: Read-only access to project resources

### Enforcement

- All API endpoints check project membership and role requirements
- CLI commands respect user's project access
- Global admins have access to all projects

## Default Project

The `default` project exists for backward compatibility and migrating existing resources.
