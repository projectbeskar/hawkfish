# HawkFish Architecture

HawkFish is designed as a cloud-native virtualization management platform that exposes a standards-compliant Redfish API while providing enterprise-grade features like multi-tenancy, live migration, and vendor compatibility.

## Core Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                            │
├─────────────────────────────────────────────────────────────────┤
│  Web UI  │  CLI  │  Python SDK  │  Terraform  │  Ansible       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     API Gateway & Auth                         │
├─────────────────────────────────────────────────────────────────┤
│         FastAPI + Authentication + Rate Limiting               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Redfish API Layer                           │
├─────────────────────────────────────────────────────────────────┤
│  Standard Endpoints  │  OEM Extensions  │  Persona Adapters    │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Business Logic Layer                         │
├─────────────────────────────────────────────────────────────────┤
│ Systems │ Profiles │ Storage │ Networks │ Tasks │ Events        │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                         │
├─────────────────────────────────────────────────────────────────┤
│    Libvirt Driver    │    Storage Pools    │    Host Manager   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Virtualization Layer                         │
├─────────────────────────────────────────────────────────────────┤
│              KVM/QEMU + libvirt + Storage                      │
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

#### HawkFish Controller
- **Technology**: FastAPI-based Python application
- **Purpose**: Main API server and orchestration engine
- **Responsibilities**:
  - Redfish API implementation
  - Authentication and authorization
  - Request routing and validation
  - Business logic orchestration

#### Persona System
- **Purpose**: Vendor-specific hardware compatibility layer
- **Supported Personas**:
  - HPE iLO 5 compatibility mode
  - Dell iDRAC 9 compatibility mode
  - Generic Redfish (default)
- **Features**:
  - API endpoint aliasing
  - Event format adaptation
  - Error message translation

#### Multi-Host Orchestrator
- **Purpose**: Distributed VM management across multiple hosts
- **Features**:
  - Intelligent VM placement
  - Load balancing
  - Live migration coordination
  - Host health monitoring

#### Storage Management
- **Supported Types**: Directory, NFS, LVM, iSCSI storage pools
- **Volume Formats**: qcow2, raw, VMDK
- **Features**:
  - Multi-pool management
  - Volume snapshots
  - Quota enforcement

#### Event System
- **Real-time Events**: Server-Sent Events (SSE) streaming
- **Durable Delivery**: Webhook subscriptions with retry logic
- **Event Types**: Power, media, task, system lifecycle events

## Data Architecture

### Database Schema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Projects     │    │     Systems     │    │    Profiles     │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ id              │◄───┤ project_id      │    │ id              │
│ name            │    │ id              │───►│ name            │
│ quotas          │    │ profile_id      │    │ cpu             │
│ created_at      │    │ host_id         │    │ memory_mib      │
└─────────────────┘    │ power_state     │    │ disk_gib        │
                       │ persona         │    │ network_config  │
                       └─────────────────┘    └─────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│      Hosts      │    │     Tasks       │    │     Events      │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ id              │    │ id              │    │ id              │
│ name            │    │ system_id       │    │ system_id       │
│ uri             │    │ state           │    │ type            │
│ labels          │    │ percent_complete│    │ timestamp       │
│ capacity        │    │ created_at      │    │ data            │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### State Management

#### Persistent State (SQLite)
- System metadata and configuration
- User accounts and sessions
- Task tracking and history
- Event subscriptions
- Project and quota information

#### Runtime State (Memory + libvirt)
- VM power states and resource allocation
- Active console sessions
- Live migration status
- Real-time metrics

#### Distributed State (Multi-host)
- Host capacity and health status
- VM placement decisions
- Migration coordination
- Storage pool availability

## Security Architecture

### Authentication & Authorization

```
┌─────────────────────────────────────────────────────────────────┐
│                   Authentication Flow                          │
├─────────────────────────────────────────────────────────────────┤
│  1. Client Login → 2. Session Token → 3. Request with Token    │
│  4. Token Validation → 5. Permission Check → 6. API Response   │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                   Authorization Model                          │
├─────────────────────────────────────────────────────────────────┤
│ Projects (Tenants)                                              │
│ ├── Users with Roles (admin, operator, viewer)                 │
│ ├── Resource Quotas (CPU, memory, disk, systems)               │
│ └── Scoped Resources (systems, profiles, images, volumes)      │
└─────────────────────────────────────────────────────────────────┘
```

### Transport Security
- **TLS Support**: Self-signed or custom certificates
- **mTLS Option**: Client certificate authentication
- **Rate Limiting**: Per-user and per-IP limits
- **CORS**: Configurable cross-origin policies

### Data Protection
- **Encryption at Rest**: SQLite database encryption option
- **Secrets Management**: Secure storage of API keys and certificates
- **Audit Logging**: Comprehensive operation tracking

## Scalability & Performance

### Horizontal Scaling

#### Multi-Controller Deployment
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Controller A  │    │   Controller B  │    │   Controller C  │
├─────────────────┤    ├─────────────────┤    ├─────────────────┤
│ Shared SQLite   │◄──►│ Shared SQLite   │◄──►│ Shared SQLite   │
│ Local Cache     │    │ Local Cache     │    │ Local Cache     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Host Pool    │    │    Host Pool    │    │    Host Pool    │
│   (Region A)    │    │   (Region B)    │    │   (Region C)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

#### Performance Optimization
- **Connection Pooling**: Efficient libvirt connection management
- **Async Operations**: Non-blocking I/O for all external calls
- **Caching**: In-memory caching of frequently accessed data
- **Batch Operations**: Bulk VM creation and management

### Resource Management

#### Host Scheduling
- **Placement Algorithms**: Spread, binpack, label-based placement
- **Resource Tracking**: Real-time CPU, memory, storage utilization
- **Health Monitoring**: Host availability and performance metrics
- **Load Balancing**: Automatic VM distribution

#### Storage Optimization
- **Thin Provisioning**: qcow2 sparse allocation
- **Deduplication**: Shared base images with copy-on-write
- **Tiered Storage**: SSD for hot data, HDD for cold storage
- **Garbage Collection**: Automatic cleanup of unused resources

## Integration Architecture

### API Compatibility

#### Standards Compliance
- **DMTF Redfish**: Full Redfish 1.6+ compatibility
- **OpenAPI 3.0**: Complete API specification
- **JSON Schema**: Request/response validation
- **HTTP Standards**: RESTful design with proper status codes

#### Vendor Extensions
- **OEM Namespace**: `/redfish/v1/Oem/HawkFish/` for extensions
- **Persona Adapters**: Vendor-specific endpoint mapping
- **Custom Properties**: Additional metadata and features

### Event Integration

#### Real-time Streaming
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   HawkFish      │    │   Event Bus     │    │   Clients       │
│   Controller    │───►│   (SSE Stream)  │───►│   (Web UI, CLI) │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Webhook       │    │   External      │    │   Monitoring    │
│   Delivery      │───►│   Systems       │───►│   (Prometheus)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

#### Event Flow
1. **Source Events**: VM state changes, task updates, system events
2. **Event Processing**: Filtering, transformation, enrichment
3. **Real-time Delivery**: SSE streams to connected clients
4. **Durable Delivery**: Webhook subscriptions with retry logic
5. **Monitoring Integration**: Metrics and alerting systems

## Deployment Patterns

### Single-Host Development
- **Components**: Controller + libvirt on single machine
- **Storage**: Local disk storage
- **Network**: Bridge networking
- **Use Case**: Development, testing, small labs

### Multi-Host Production
- **Components**: Multiple controllers + host pool
- **Storage**: Shared storage (NFS, Ceph, etc.)
- **Network**: VLAN isolation, multiple networks
- **Use Case**: Production environments, large-scale deployments

### Cloud-Native Kubernetes
- **Components**: Controller pods + persistent volumes
- **Storage**: Container Storage Interface (CSI)
- **Network**: CNI-based networking
- **Use Case**: Cloud deployments, managed services

### Hybrid Cloud
- **Components**: On-premises + cloud instances
- **Storage**: Hybrid storage pools
- **Network**: VPN/peering connections
- **Use Case**: Disaster recovery, cloud bursting

## Future Architecture Considerations

### Planned Enhancements
- **High Availability**: Controller clustering with leader election
- **Database Scaling**: PostgreSQL support for large deployments
- **GPU Support**: GPU passthrough and virtualization
- **Container Integration**: Kubernetes VM orchestration
- **Advanced Networking**: SDN integration, network automation

### Extensibility
- **Plugin System**: Custom drivers and extensions
- **Custom Personas**: User-defined hardware compatibility
- **Workflow Engine**: Complex automation and orchestration
- **API Versioning**: Backward compatibility and evolution


