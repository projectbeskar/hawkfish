# HawkFish Terraform Provider Example

This directory contains an example Terraform configuration for managing HawkFish resources.

## Prerequisites

1. **HawkFish Controller** running at `http://localhost:8080`
2. **Terraform Provider** (to be implemented separately)

## Provider Resources

The HawkFish Terraform provider would support these resources:

### `hawkfish_profile`
Manages node profiles (templates for VM specifications).

```hcl
resource "hawkfish_profile" "small" {
  name        = "small-vm"
  cpu         = 2
  memory_mib  = 2048
  disk_gib    = 20
  network     = "default"
  boot_primary = "Hdd"
}
```

### `hawkfish_system`
Manages virtual systems (VMs).

```hcl
resource "hawkfish_system" "vm1" {
  name       = "my-vm"
  profile_id = hawkfish_profile.small.id
  
  tags = {
    environment = "production"
  }
}
```

### `hawkfish_power`
Manages system power state.

```hcl
resource "hawkfish_power" "vm1_power" {
  system_id  = hawkfish_system.vm1.id
  reset_type = "On"
}
```

### `hawkfish_subscription`
Manages event subscriptions.

```hcl
resource "hawkfish_subscription" "webhook" {
  destination = "https://webhook.example.com/events"
  event_types = ["PowerStateChanged"]
  system_ids  = [hawkfish_system.vm1.id]
}
```

## Data Sources

### `hawkfish_systems`
Retrieve information about existing systems.

```hcl
data "hawkfish_systems" "all" {
  filter = "tag:environment=production"
}
```

### `hawkfish_profiles`
Retrieve available profiles.

```hcl
data "hawkfish_profiles" "available" {}
```

## Usage

1. **Initialize Terraform**:
   ```bash
   terraform init
   ```

2. **Plan deployment**:
   ```bash
   terraform plan
   ```

3. **Apply configuration**:
   ```bash
   terraform apply
   ```

4. **Clean up**:
   ```bash
   terraform destroy
   ```

## Configuration

Set provider configuration via variables:

```bash
export TF_VAR_hawkfish_endpoint="https://hawkfish.example.com"
export TF_VAR_hawkfish_username="admin"
export TF_VAR_hawkfish_password="secret"
```

Or create a `terraform.tfvars` file:

```hcl
hawkfish_endpoint = "https://hawkfish.example.com"
hawkfish_username = "admin"
hawkfish_password = "secret"
```

## Provider Implementation

The HawkFish Terraform provider would be implemented in Go using the [Terraform Plugin Framework](https://developer.hashicorp.com/terraform/plugin/framework).

Key components:
- **Provider**: Authentication and configuration
- **Resources**: CRUD operations for profiles, systems, power states, subscriptions
- **Data Sources**: Read-only access to systems, profiles, tasks
- **Client**: HTTP client for HawkFish Redfish API

See `provider/` directory for implementation skeleton.
