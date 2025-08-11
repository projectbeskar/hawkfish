### HawkFish v0.5.0

Major enhancements focused on multi-host orchestration, image management, and durable event delivery.

#### New Features

**Host Pools & Scheduler**
- Multi-host libvirt management with automatic VM placement
- Host capacity tracking and label-based constraints
- Intelligent scheduling using spread algorithm
- API: `/redfish/v1/Oem/HawkFish/Hosts`
- CLI: `hawkfish hosts`, `host-add`, `host-rm`

**Persistent Adoption Mapping**
- Stable mapping between libvirt domains and Redfish Systems
- Adoption persistence across service restarts
- Host-aware adoption with lifecycle tracking
- API: `/redfish/v1/Oem/HawkFish/Import/Adoptions`
- CLI: `hawkfish adoptions`

**Image Catalog**
- Versioned base image management with SHA256 verification
- Automatic download and caching from URLs
- Garbage collection for unreferenced images
- API: `/redfish/v1/Oem/HawkFish/Images`
- CLI: `hawkfish images`, `image-add`, `image-rm`

**Durable Event Delivery**
- Async webhook delivery with exponential backoff
- Persistent outbound queue with retry logic (up to 5 attempts)
- Dead letter handling for failed deliveries
- Background worker with configurable concurrency
- Maintains SSE streaming for real-time events

**Network Profiles**
- Templated network configurations for VM deployment
- Support for libvirt networks, bridges, and VLAN tagging
- Multiple NICs per system with auto/fixed MAC policies
- Cloud-init network-config generation with template expansion
- API: `/redfish/v1/Oem/HawkFish/NetworkProfiles`
- CLI: `hawkfish netprofiles`, `netprofile-create`, `netprofile-rm`

#### Enhancements

**Orchestrator Integration**
- Host placement in VM creation workflow
- Resource allocation tracking per host
- Label-based placement constraints

**Documentation**
- New guides: hosts.md, images.md, network-profiles.md, events-durability.md
- Updated quickstart with new CLI examples
- Comprehensive API coverage

#### Quality & Testing

- All new APIs include JSON Schema validation
- Comprehensive error handling and Redfish-style responses
- Thread-safe background workers
- Deterministic testing support
- Lint/type clean across codebase

#### Database Schema

New tables added:
- `hf_hosts`: Host pool management
- `hf_adoptions`: Persistent domain mappings
- `hf_images`: Image catalog with metadata
- `hf_netprofiles`: Network profile templates
- `hf_outbox`: Durable event delivery queue

#### Breaking Changes

- EventService delivery is now asynchronous by default
- Host pools are required for new VM placement (auto-creates localhost if none exist)

#### Migration Notes

Existing installations will automatically create necessary database tables on first run. No manual migration required.
