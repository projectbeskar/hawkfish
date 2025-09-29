# HawkFish Documentation

HawkFish is a fully virtual "bare-metal" lab platform that uses Linux KVM/libvirt to emulate hardware and exposes a DMTF Redfish API for provisioning, power control, boot media, and events.

## Table of Contents

### Getting Started
- [Quickstart Guide](quickstart.md) - Get HawkFish running in minutes
- [Architecture Overview](architecture.md) - Understanding HawkFish's design
- [Installation Requirements](requirements.md) - System requirements and dependencies

### Core Features
- [Systems Management](systems.md) - Virtual machine lifecycle management
- [Profiles & Templates](profiles.md) - VM configuration templates
- [Storage Management](storage-pools.md) - Storage pools and volume operations
- [Network Profiles](network-profiles.md) - Network configuration templates
- [Image Catalog](images.md) - Base image management and versioning

### Advanced Features
- [Multi-Tenancy & Projects](tenancy.md) - Project isolation and resource quotas
- [Live Migration](migration.md) - Moving VMs between hosts with minimal downtime
- [Host Management](hosts.md) - Multi-host orchestration and scheduling
- [Console Access](console.md) - WebSocket-based console sessions
- [Snapshots & Backup](snapshots.md) - VM state management and data protection

### Hardware Compatibility
- [Persona System](personas.md) - Vendor-specific compatibility layer
- [HPE iLO Integration](persona-ilo.md) - HPE iLO compatibility mode
- [Dell iDRAC Integration](persona-idrac.md) - Dell iDRAC compatibility mode
- [Redfish Conformance](conformance.md) - Standards compliance and testing

### Events & Monitoring
- [Event System](events.md) - Real-time event streaming and webhooks
- [Event Durability](events-durability.md) - Reliable event delivery
- [Metrics & Monitoring](monitoring.md) - Prometheus metrics and observability
- [Audit Logging](audit.md) - Security and compliance logging

### Automation & Integration
- [Batch Operations](batch.md) - Bulk VM creation and management
- [Task Management](tasks.md) - Asynchronous operation tracking
- [Python SDK](sdk-python.md) - Programmatic API access
- [Terraform Provider](automation.md#terraform) - Infrastructure as Code
- [Ansible Collection](automation.md#ansible) - Configuration management
- [Import & Adoption](import.md) - Existing VM integration

### Operations
- [Deployment Guide](deploy.md) - Production deployment patterns
- [Operations Guide](ops.md) - Backup, recovery, and maintenance
- [Performance & Scale](scale-performance.md) - Tuning and capacity planning
- [Security Guide](security.md) - Authentication, authorization, and TLS
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

### User Interface
- [Web UI Guide](ui.md) - React-based management interface
- [CLI Reference](cli.md) - Command-line tool usage

### API Reference
- [Redfish API](api-redfish.md) - Standard Redfish endpoints
- [HawkFish Extensions](api-extensions.md) - Custom OEM endpoints
- [Authentication](api-auth.md) - API authentication and sessions
- [Error Handling](api-errors.md) - Error responses and troubleshooting

### Release Information
- [v0.8.0 Release Notes](release-notes-0.8.0.md) - Current release
- [v0.7.0 Release Notes](release-notes-0.7.0.md) - Previous releases
- [v0.5.0 Release Notes](release-notes-0.5.0.md)
- [v0.4.0 Release Notes](release-notes-0.4.0.md)

## Quick Links

### Essential Reading
1. [Quickstart Guide](quickstart.md) - Start here for new users
2. [Architecture Overview](architecture.md) - Understand the system design
3. [Deployment Guide](deploy.md) - Production setup instructions

### Common Tasks
- [Creating VMs](systems.md#creating-systems) - System creation workflows
- [Setting up Personas](personas.md#configuration) - Hardware compatibility
- [Configuring Storage](storage-pools.md#setup) - Storage pool management
- [Event Subscriptions](events.md#subscriptions) - Webhook configuration

### Development
- [Contributing Guidelines](../CONTRIBUTING.md) - Development setup and standards
- [API Examples](../examples/) - Sample code and scripts
- [Testing](testing.md) - Test suite and validation

## Support

- **Issues**: Report bugs and feature requests on GitHub
- **Documentation**: This documentation is versioned with the code
- **API**: Interactive API documentation available at `/redfish/v1/docs`
- **Examples**: Complete examples in the [`examples/`](../examples/) directory

## License

HawkFish is released under the Apache-2.0 License. See [LICENSE](../LICENSE) for details.
