# HawkFish Examples

This directory contains comprehensive examples demonstrating HawkFish functionality across different use cases and integration patterns.

## Quick Start Examples

### Basic API Usage
- [`basic_operations.py`](basic_operations.py) - Essential API operations (power, media, systems)
- [`authentication_example.py`](authentication_example.py) - Login and session management
- [`event_streaming.py`](event_streaming.py) - Real-time event monitoring with SSE

### System Management
- [`system_lifecycle.py`](system_lifecycle.py) - Complete VM lifecycle from creation to deletion
- [`batch_operations.py`](batch_operations.py) - Bulk system creation and management
- [`live_migration.py`](live_migration.py) - Moving VMs between hosts

## Hardware Persona Examples

### HPE iLO Integration
- [`ilo/`](ilo/) - HPE iLO compatibility examples
  - [`ilo_bios_workflow.py`](ilo/ilo_bios_workflow.py) - BIOS configuration with ApplyTime staging
  - [`ilo_virtual_media_example.sh`](ilo/ilo_virtual_media_example.sh) - Media operations via iLO endpoints
  - [`ilo_console_access.py`](ilo/ilo_console_access.py) - Console session management

### Dell iDRAC Integration  
- [`idrac/`](idrac/) - Dell iDRAC compatibility examples
  - [`idrac_virtual_media_example.sh`](idrac/idrac_virtual_media_example.sh) - Media operations via iDRAC endpoints
  - [`idrac_job_management.py`](idrac/idrac_job_management.py) - Job queue and task management
  - [`idrac_configuration.py`](idrac/idrac_configuration.py) - System configuration workflows

## Infrastructure as Code

### Terraform
- [`terraform/`](terraform/) - Terraform provider examples
  - [`main.tf`](terraform/main.tf) - Basic resource management
  - [`multi_tier_app.tf`](terraform/multi_tier_app.tf) - Complex application deployment
  - [`variables.tf`](terraform/variables.tf) - Configuration variables
  - [`README.md`](terraform/README.md) - Setup and usage instructions

### Ansible
- [`ansible/`](ansible/) - Ansible collection examples
  - [`playbook.yml`](ansible/playbook.yml) - VM lifecycle playbook
  - [`inventory`](ansible/inventory) - Dynamic inventory configuration
  - [`roles/`](ansible/roles/) - Reusable automation roles
  - [`README.md`](ansible/README.md) - Collection setup and usage

## SDK and Integration

### Python SDK
- [`sdk/`](sdk/) - Python client library examples
  - [`python_client.py`](sdk/python_client.py) - Basic SDK usage
  - [`async_operations.py`](sdk/async_operations.py) - Asynchronous operations
  - [`bulk_management.py`](sdk/bulk_management.py) - Large-scale operations
  - [`custom_workflows.py`](sdk/custom_workflows.py) - Advanced automation patterns

### REST API Examples
- [`rest_api/`](rest_api/) - Direct REST API usage
  - [`curl_examples.sh`](rest_api/curl_examples.sh) - Complete curl command reference
  - [`postman_collection.json`](rest_api/postman_collection.json) - Postman API collection
  - [`api_testing.py`](rest_api/api_testing.py) - API validation and testing

## Advanced Use Cases

### Multi-Tenancy
- [`multi_tenant/`](multi_tenant/) - Project-based isolation examples
  - [`project_setup.py`](multi_tenant/project_setup.py) - Project creation and management
  - [`quota_management.py`](multi_tenant/quota_management.py) - Resource quota enforcement
  - [`rbac_examples.py`](multi_tenant/rbac_examples.py) - Role-based access control

### Storage Management
- [`storage/`](storage/) - Storage pool and volume examples
  - [`storage_pools.py`](storage/storage_pools.py) - Pool creation and management
  - [`volume_operations.py`](storage/volume_operations.py) - Volume lifecycle
  - [`snapshot_management.py`](storage/snapshot_management.py) - Snapshot and backup operations

### Monitoring and Events
- [`monitoring/`](monitoring/) - Observability examples
  - [`prometheus_metrics.py`](monitoring/prometheus_metrics.py) - Metrics collection
  - [`webhook_handler.py`](monitoring/webhook_handler.py) - Event webhook processing
  - [`alerting_rules.yml`](monitoring/alerting_rules.yml) - Prometheus alerting rules

## Development and Testing

### Testing Examples
- [`testing/`](testing/) - Testing patterns and utilities
  - [`integration_tests.py`](testing/integration_tests.py) - Full workflow testing
  - [`performance_tests.py`](testing/performance_tests.py) - Load and performance testing
  - [`mock_scenarios.py`](testing/mock_scenarios.py) - Development testing utilities

### Custom Extensions
- [`extensions/`](extensions/) - Custom persona and plugin examples
  - [`custom_persona.py`](extensions/custom_persona.py) - Custom hardware persona
  - [`webhook_plugins.py`](extensions/webhook_plugins.py) - Event processing plugins
  - [`api_extensions.py`](extensions/api_extensions.py) - Custom API endpoints

## Docker and Kubernetes

### Containerized Deployment
- [`docker/`](docker/) - Docker deployment examples
  - [`docker-compose.yml`](docker/docker-compose.yml) - Multi-service deployment
  - [`Dockerfile.custom`](docker/Dockerfile.custom) - Custom image examples
  - [`health_checks.sh`](docker/health_checks.sh) - Container health monitoring

### Kubernetes
- [`kubernetes/`](kubernetes/) - Kubernetes deployment examples
  - [`hawkfish-deployment.yaml`](kubernetes/hawkfish-deployment.yaml) - Basic deployment
  - [`helm-values.yaml`](kubernetes/helm-values.yaml) - Helm chart configuration
  - [`operators/`](kubernetes/operators/) - Kubernetes operator examples

## Getting Started

### Prerequisites

Most examples require:
- HawkFish controller running (see [Quickstart Guide](../docs/quickstart.md))
- Valid authentication token
- Python 3.11+ (for Python examples)

### Environment Setup

Set these environment variables for all examples:

```bash
export HAWKFISH_URL="http://localhost:8080"
export HAWKFISH_TOKEN="your-session-token"
export SYSTEM_ID="your-system-id"  # For system-specific examples
```

### Running Examples

#### Python Examples
```bash
# Install dependencies
pip install hawkfish[dev]

# Run basic operations
python examples/basic_operations.py

# Run with custom configuration
HAWKFISH_URL=https://hawkfish.local:8443 python examples/system_lifecycle.py
```

#### Shell Script Examples
```bash
# Make executable
chmod +x examples/ilo/ilo_virtual_media_example.sh

# Run with environment variables
./examples/ilo/ilo_virtual_media_example.sh
```

#### Infrastructure Examples
```bash
# Terraform
cd examples/terraform
terraform init
terraform plan
terraform apply

# Ansible
cd examples/ansible
ansible-playbook -i inventory playbook.yml
```

## Example Categories

### By Complexity Level

#### Beginner
- Basic operations
- Simple API calls
- Single-system management

#### Intermediate  
- Multi-system operations
- Persona integration
- Event handling

#### Advanced
- Custom workflows
- Infrastructure automation
- Performance optimization

### By Use Case

#### Development
- Testing utilities
- Mock environments
- Local development

#### Production
- Deployment automation
- Monitoring integration
- Disaster recovery

#### Integration
- Third-party tools
- Custom applications
- Hybrid workflows

## Contributing Examples

### Guidelines

1. **Clear Documentation**: Include comprehensive comments and README files
2. **Error Handling**: Demonstrate proper error handling patterns
3. **Configuration**: Use environment variables for configurable values
4. **Testing**: Include validation and testing approaches
5. **Real-world Focus**: Address practical use cases

### Example Template

```python
#!/usr/bin/env python3
"""
Brief description of what this example demonstrates.

Prerequisites:
- List any specific requirements
- Environment variables needed
- System state assumptions

Usage:
    python example_name.py [arguments]

Environment Variables:
    HAWKFISH_URL - HawkFish controller URL
    HAWKFISH_TOKEN - Authentication token
"""

import os
import sys
# Additional imports

def main():
    """Main example function with error handling."""
    # Configuration
    base_url = os.getenv("HAWKFISH_URL", "http://localhost:8080")
    token = os.getenv("HAWKFISH_TOKEN")
    
    if not token:
        print("ERROR: HAWKFISH_TOKEN environment variable required")
        sys.exit(1)
    
    # Example implementation
    try:
        # Your example code here
        pass
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Support and Resources

- **Documentation**: [HawkFish Documentation](../docs/)
- **API Reference**: Available at `/redfish/v1/docs` on your HawkFish instance
- **Issues**: Report problems or request examples via GitHub Issues
- **Community**: Join discussions about examples and best practices

## License

All examples are provided under the same license as HawkFish (Apache-2.0).
See [LICENSE](../LICENSE) for details.
