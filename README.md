# HawkFish

**A cloud-native virtualization management platform with DMTF Redfish API compatibility**

HawkFish provides a fully virtual "bare-metal" lab environment using Linux KVM/libvirt, exposing enterprise-grade virtualization management through a standards-compliant Redfish API. Perfect for development, testing, and educational environments that need realistic hardware management interfaces without physical servers.

## Key Features

### Standards Compliance
- **DMTF Redfish API** - Full compatibility with Redfish 1.6+ specifications
- **Vendor Personas** - HPE iLO and Dell iDRAC compatibility modes
- **OpenAPI Documentation** - Complete API specification and interactive docs

### Enterprise Features
- **Multi-Tenancy** - Project-based isolation with role-based access control
- **Live Migration** - Move running VMs between hosts with minimal downtime
- **Storage Management** - Support for multiple storage pool types and formats
- **Event System** - Real-time events via SSE and webhook subscriptions
- **Console Access** - WebSocket-based console sessions with security

### Modern Architecture
- **Cloud-Native** - Kubernetes-ready with Helm charts and container support
- **Scalable** - Multi-host orchestration with intelligent VM placement
- **Observable** - Prometheus metrics, audit logging, and comprehensive monitoring
- **Extensible** - Plugin system for custom personas and workflows

## Quick Start

### Prerequisites
- **Linux host** with Python 3.11+ (Ubuntu 22.04+ recommended)
- **Optional**: KVM/libvirt for full VM functionality

### Installation

#### Development Setup
```bash
# Clone and install
git clone https://github.com/your-org/HawkFish.git
cd HawkFish
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]

# Start controller
hawkfish-controller --host 0.0.0.0 --port 8080
```

#### Production Install
```bash
# Install from PyPI
pip install hawkfish[virt]

# Or use Docker
docker run -p 8080:8080 hawkfish/hawkfish-controller:latest
```

### First Steps

```bash
# Check API is running
curl -s http://localhost:8080/redfish/v1/ | jq .

# Login and get token
export HAWKFISH_TOKEN=$(curl -s -X POST http://localhost:8080/redfish/v1/SessionService/Sessions \
  -H "Content-Type: application/json" \
  -d '{"UserName":"local","Password":""}' | jq -r .SessionToken)

# Create a VM profile
curl -X POST http://localhost:8080/redfish/v1/Oem/HawkFish/Profiles \
  -H "X-Auth-Token: $HAWKFISH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Name": "small-vm",
    "CPU": 2,
    "MemoryMiB": 2048,
    "DiskGiB": 20,
    "Network": "default"
  }'

# Create and start a VM
curl -X POST http://localhost:8080/redfish/v1/Systems \
  -H "X-Auth-Token: $HAWKFISH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"Name": "test-vm", "ProfileId": "small-vm"}'

# Power on the VM
curl -X POST http://localhost:8080/redfish/v1/Systems/test-vm/Actions/ComputerSystem.Reset \
  -H "X-Auth-Token: $HAWKFISH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"ResetType": "On"}'
```

## Use Cases

### Development & Testing
- **API Development** - Test Redfish client applications without physical hardware
- **CI/CD Integration** - Automated testing with disposable VM environments
- **Education** - Learn BMC/IPMI concepts with realistic interfaces

### Lab Environments
- **Hardware Emulation** - Simulate data center environments for training
- **Integration Testing** - Test management tools against various "hardware" types
- **Proof of Concepts** - Validate designs before physical deployment

### Automation & Orchestration
- **Infrastructure as Code** - Terraform and Ansible integration
- **Hybrid Management** - Unified interface for physical and virtual infrastructure
- **Migration Testing** - Practice migration scenarios safely

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Clients: Web UI, CLI, Terraform, Ansible, Python SDK         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              FastAPI + Redfish API + Authentication            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│    Persona System: Generic, HPE iLO, Dell iDRAC Compatibility  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│      Business Logic: Systems, Storage, Networks, Tasks         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              KVM/libvirt + Storage Pools + Networking          │
└─────────────────────────────────────────────────────────────────┘
```

## Documentation

### Getting Started
- [**Quickstart Guide**](docs/quickstart.md) - Get running in minutes
- [**Installation Requirements**](docs/requirements.md) - System requirements and dependencies
- [**Architecture Overview**](docs/architecture.md) - Understanding HawkFish design

### User Guides
- [**Systems Management**](docs/systems.md) - VM lifecycle management
- [**Storage & Networking**](docs/storage-pools.md) - Storage and network configuration
- [**Multi-Tenancy**](docs/tenancy.md) - Projects and resource isolation
- [**Hardware Personas**](docs/personas.md) - Vendor compatibility modes

### Operations
- [**Deployment Guide**](docs/deploy.md) - Production deployment patterns
- [**Operations Manual**](docs/ops.md) - Backup, monitoring, maintenance
- [**Performance Tuning**](docs/scale-performance.md) - Optimization and scaling

### Integration
- [**Python SDK**](examples/sdk/) - Programmatic access examples
- [**Terraform Provider**](examples/terraform/) - Infrastructure as Code
- [**Ansible Collection**](examples/ansible/) - Configuration management
- [**API Reference**](docs/) - Complete API documentation

## Examples

HawkFish includes comprehensive examples for common scenarios:

```bash
# Basic operations
python examples/basic_operations.py

# Complete VM lifecycle
python examples/system_lifecycle.py

# HPE iLO compatibility
python examples/ilo/ilo_bios_workflow.py

# Infrastructure as Code
cd examples/terraform && terraform apply

# Configuration management
ansible-playbook examples/ansible/playbook.yml
```

See [`examples/`](examples/) directory for complete examples with documentation.

## Web Interface

HawkFish includes a modern React-based web interface:

```bash
# Enable web UI
export HF_UI_ENABLED=true
hawkfish-controller

# Access at http://localhost:8080/ui/
```

Features:
- Real-time system monitoring
- Power and boot management
- Virtual media operations
- Event streaming
- Mobile-responsive design

## Deployment Options

### Single Host (Development)
```bash
# Local development
hawkfish-controller --host 0.0.0.0 --port 8080
```

### Docker Compose
```bash
# Production-ready stack
cd deploy/compose
docker-compose up -d
```

### Kubernetes
```bash
# Helm deployment
helm repo add hawkfish https://charts.hawkfish.local
helm install hawkfish hawkfish/hawkfish-controller
```

### Configuration

Key environment variables:

```bash
# Basic configuration
export HF_HOST=0.0.0.0
export HF_PORT=8080
export HF_UI_ENABLED=true

# Security
export HF_DEV_TLS=self-signed
export HF_AUTH_REQUIRED=true

# Performance
export HF_WORKER_COUNT=4
export HF_CONNECTION_POOL_SIZE=20

# Storage
export HF_DATA_DIR=/var/lib/hawkfish
export HF_ISO_PATH=/var/lib/hawkfish/isos
```

See [deployment guide](docs/deploy.md) for complete configuration options.

## Hardware Compatibility

### Vendor Personas

HawkFish can emulate specific hardware vendor interfaces:

```bash
# Set HPE iLO persona
hawkfish persona set web-01 hpe_ilo5

# Access via iLO-compatible endpoints
curl http://localhost:8080/redfish/v1/Managers/iLO.Embedded.1

# Set Dell iDRAC persona
hawkfish persona set web-02 dell_idrac9

# Access via iDRAC-compatible endpoints
curl http://localhost:8080/redfish/v1/Managers/iDRAC.Embedded.1
```

This enables existing tools and scripts to work unchanged with HawkFish.

## Monitoring & Observability

### Metrics
```bash
# Prometheus metrics
curl http://localhost:8080/redfish/v1/metrics
```

### Events
```bash
# Real-time event stream
curl -H "Accept: text/event-stream" \
     http://localhost:8080/redfish/v1/EventService/Subscriptions/SSE

# Webhook subscriptions
curl -X POST http://localhost:8080/redfish/v1/EventService/Subscriptions \
  -H "X-Auth-Token: $TOKEN" \
  -d '{"Destination": "https://your-webhook.com/events"}'
```

### Audit Logging
All operations are comprehensively logged for security and compliance.

## Community & Support

### Getting Help
- **Documentation**: [Complete docs](docs/) with examples and tutorials
- **Issues**: [GitHub Issues](https://github.com/your-org/HawkFish/issues) for bugs and feature requests
- **Discussions**: [GitHub Discussions](https://github.com/your-org/HawkFish/discussions) for questions and ideas

### Contributing
We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Roadmap
- **GPU Support** - GPU passthrough and virtualization
- **Advanced Networking** - SDN integration and network automation
- **HA Mode** - Controller clustering with leader election
- **Cloud Integration** - Cloud provider plugins and hybrid management

## License

HawkFish is released under the [Apache-2.0 License](LICENSE).

## Related Projects

- **[DMTF Redfish](https://www.dmtf.org/standards/redfish)** - Industry standard APIs
- **[libvirt](https://libvirt.org/)** - Virtualization management library
- **[KVM](https://www.linux-kvm.org/)** - Kernel-based Virtual Machine
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern Python web framework

---

**Ready to get started?** Check out the [Quickstart Guide](docs/quickstart.md) or explore the [Examples](examples/) directory.


