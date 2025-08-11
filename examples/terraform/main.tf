# HawkFish Terraform Example
# This demonstrates basic resource management with HawkFish

terraform {
  required_providers {
    hawkfish = {
      source  = "local/hawkfish"
      version = "~> 0.1"
    }
  }
}

provider "hawkfish" {
  endpoint = var.hawkfish_endpoint
  username = var.hawkfish_username
  password = var.hawkfish_password
}

# Create a profile for small VMs
resource "hawkfish_profile" "small" {
  name        = "terraform-small"
  cpu         = 2
  memory_mib  = 2048
  disk_gib    = 20
  network     = "default"
  boot_primary = "Hdd"
}

# Create a system from the profile
resource "hawkfish_system" "demo" {
  name       = "terraform-demo-vm"
  profile_id = hawkfish_profile.small.id
  
  tags = {
    environment = "demo"
    created_by  = "terraform"
  }
}

# Power on the system
resource "hawkfish_power" "demo_power" {
  system_id   = hawkfish_system.demo.id
  reset_type  = "On"
  
  depends_on = [hawkfish_system.demo]
}

# Create an event subscription
resource "hawkfish_subscription" "demo_events" {
  destination = "https://webhook.example.com/hawkfish"
  event_types = ["PowerStateChanged", "TaskUpdated"]
  system_ids  = [hawkfish_system.demo.id]
}

# Outputs
output "system_id" {
  description = "ID of the created system"
  value       = hawkfish_system.demo.id
}

output "system_power_state" {
  description = "Current power state"
  value       = hawkfish_system.demo.power_state
}

output "profile_id" {
  description = "ID of the created profile"
  value       = hawkfish_profile.small.id
}
