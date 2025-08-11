# HawkFish Automation Guide

This guide covers automation integration with HawkFish using various tools and SDKs.

## SDKs and Client Libraries

### Python SDK

#### Installation

```bash
# Install from PyPI (when published)
pip install hawkfish-client

# Or use the example client
curl -O https://raw.githubusercontent.com/projectbeskar/hawkfish/main/examples/sdk/python_client.py
```

#### Basic Usage

```python
import asyncio
from hawkfish_client import HawkFishClient

async def main():
    async with HawkFishClient("http://localhost:8080") as client:
        # Authenticate
        await client.login("admin", "password")
        
        # List systems
        systems = await client.list_systems()
        print(f"Found {len(systems['Members'])} systems")
        
        # Power on a system
        if systems['Members']:
            system_id = systems['Members'][0]['Id']
            await client.power_action(system_id, "On")
            print(f"Powered on system {system_id}")

asyncio.run(main())
```

#### Advanced Examples

```python
# Create a system from profile
async def provision_vm():
    async with HawkFishClient("http://localhost:8080") as client:
        await client.login("admin", "password")
        
        # Create profile
        profile_spec = {
            "Name": "web-server",
            "CPU": 4,
            "MemoryMiB": 4096,
            "DiskGiB": 50,
            "Network": "default",
            "Boot": {"Primary": "Hdd"}
        }
        profile_id = await client.create_profile(profile_spec)
        
        # Create system
        task_id = await client.create_system_from_profile(
            profile_id, "web-01"
        )
        
        # Wait for completion
        while True:
            task = await client.get_task(task_id)
            if task['TaskState'] in ['Completed', 'Exception']:
                break
            await asyncio.sleep(2)
        
        return task['TaskState'] == 'Completed'

# Batch operations
async def bulk_power_control():
    async with HawkFishClient("http://localhost:8080") as client:
        await client.login("admin", "password")
        
        systems = await client.list_systems()
        
        # Power on all systems concurrently
        tasks = []
        for system in systems['Members']:
            if system.get('PowerState') == 'Off':
                task = client.power_action(system['Id'], 'On')
                tasks.append(task)
        
        await asyncio.gather(*tasks)
        print(f"Powered on {len(tasks)} systems")
```

### Go SDK

#### Installation

```bash
go get github.com/projectbeskar/hawkfish-go-sdk
```

#### Usage

```go
package main

import (
    "context"
    "fmt"
    "log"
    
    "github.com/projectbeskar/hawkfish-go-sdk/client"
)

func main() {
    // Create client
    c := client.New("http://localhost:8080")
    
    // Authenticate
    err := c.Login(context.Background(), "admin", "password")
    if err != nil {
        log.Fatal(err)
    }
    
    // List systems
    systems, err := c.ListSystems(context.Background())
    if err != nil {
        log.Fatal(err)
    }
    
    fmt.Printf("Found %d systems\n", len(systems.Members))
    
    // Power actions
    for _, system := range systems.Members {
        if system.PowerState == "Off" {
            err := c.PowerAction(context.Background(), system.ID, "On")
            if err != nil {
                log.Printf("Error powering on %s: %v", system.ID, err)
            } else {
                fmt.Printf("Powered on system %s\n", system.ID)
            }
        }
    }
}
```

## Terraform Integration

### Provider Installation

```hcl
terraform {
  required_providers {
    hawkfish = {
      source  = "projectbeskar/hawkfish"
      version = "~> 0.1"
    }
  }
}

provider "hawkfish" {
  endpoint = var.hawkfish_endpoint
  username = var.hawkfish_username
  password = var.hawkfish_password
}
```

### Resource Examples

#### Managing Profiles

```hcl
# Create reusable profiles
resource "hawkfish_profile" "web_server" {
  name        = "web-server"
  cpu         = 4
  memory_mib  = 4096
  disk_gib    = 50
  network     = "bridge"
  boot_primary = "Hdd"
  
  cloud_init = {
    user_data = base64encode(templatefile("cloud-init.yml", {
      hostname = "web-{name}"
    }))
  }
}

resource "hawkfish_profile" "database" {
  name        = "database"
  cpu         = 8
  memory_mib  = 8192
  disk_gib    = 100
  network     = "bridge"
  boot_primary = "Hdd"
  
  cloud_init = {
    user_data = base64encode(file("db-cloud-init.yml"))
  }
}
```

#### Infrastructure as Code

```hcl
# Web tier
resource "hawkfish_system" "web_servers" {
  count      = 3
  name       = "web-${count.index + 1}"
  profile_id = hawkfish_profile.web_server.id
  
  tags = {
    tier        = "web"
    environment = "production"
    index       = count.index + 1
  }
}

# Database tier
resource "hawkfish_system" "database" {
  name       = "db-primary"
  profile_id = hawkfish_profile.database.id
  
  tags = {
    tier        = "database"
    environment = "production"
    role        = "primary"
  }
}

# Power management
resource "hawkfish_power" "web_power" {
  count     = length(hawkfish_system.web_servers)
  system_id = hawkfish_system.web_servers[count.index].id
  reset_type = "On"
  
  depends_on = [hawkfish_system.web_servers]
}

# Event monitoring
resource "hawkfish_subscription" "monitoring" {
  destination = "https://monitoring.example.com/webhook"
  event_types = [
    "PowerStateChanged",
    "TaskUpdated",
    "SystemCreated"
  ]
  
  system_ids = concat(
    hawkfish_system.web_servers[*].id,
    [hawkfish_system.database.id]
  )
}
```

#### Data Sources

```hcl
# Query existing systems
data "hawkfish_systems" "production" {
  filter = "tag:environment=production"
}

# Use existing profiles
data "hawkfish_profiles" "available" {}

locals {
  prod_systems = data.hawkfish_systems.production.systems
  web_systems  = [for s in local.prod_systems : s if s.tags.tier == "web"]
}

# Output system information
output "web_server_ips" {
  value = [for s in local.web_systems : {
    name = s.name
    id   = s.id
    ip   = s.primary_ip
  }]
}
```

### Terraform Workflows

#### Development Environment

```bash
# Initialize
terraform init

# Plan deployment
terraform plan -var-file="dev.tfvars"

# Apply
terraform apply -var-file="dev.tfvars"

# Scale web tier
terraform apply -var="web_server_count=5"

# Destroy environment
terraform destroy -var-file="dev.tfvars"
```

#### Production Deployment

```bash
# Use remote state
terraform init -backend-config="bucket=my-terraform-state"

# Plan with approval
terraform plan -var-file="prod.tfvars" -out=prod.plan
terraform apply prod.plan

# Gradual rollout
terraform apply -target=hawkfish_system.web_servers[0]
terraform apply -target=hawkfish_system.web_servers[1]
```

## Ansible Integration

### Collection Installation

```bash
# Install collection (when published)
ansible-galaxy collection install hawkfish.virtualization

# Or use playbook examples directly
git clone https://github.com/projectbeskar/hawkfish.git
cd hawkfish/examples/ansible/
```

### Playbook Examples

#### System Lifecycle Management

```yaml
---
- name: Provision web servers
  hosts: localhost
  vars:
    hawkfish_endpoint: "{{ vault_hawkfish_endpoint }}"
    hawkfish_username: "{{ vault_hawkfish_username }}"
    hawkfish_password: "{{ vault_hawkfish_password }}"
  
  tasks:
    - name: Create web server profile
      hawkfish.virtualization.hawkfish_profile:
        endpoint: "{{ hawkfish_endpoint }}"
        username: "{{ hawkfish_username }}"
        password: "{{ hawkfish_password }}"
        name: "web-server-profile"
        cpu: 4
        memory_mib: 4096
        disk_gib: 50
        network: "bridge"
        boot_primary: "Hdd"
        state: present
      register: web_profile

    - name: Create web servers
      hawkfish.virtualization.hawkfish_system:
        endpoint: "{{ hawkfish_endpoint }}"
        username: "{{ hawkfish_username }}"
        password: "{{ hawkfish_password }}"
        name: "web-{{ item }}"
        profile_id: "{{ web_profile.profile.id }}"
        tags:
          role: webserver
          tier: frontend
          environment: production
        state: present
      loop: "{{ range(1, web_server_count + 1) | list }}"
      register: web_servers

    - name: Power on web servers
      hawkfish.virtualization.hawkfish_power:
        endpoint: "{{ hawkfish_endpoint }}"
        username: "{{ hawkfish_username }}"
        password: "{{ hawkfish_password }}"
        system_id: "{{ item.system.id }}"
        reset_type: "On"
        wait: true
        timeout: 300
      loop: "{{ web_servers.results }}"
      when: item.system is defined
```

#### Rolling Updates

```yaml
---
- name: Rolling update web servers
  hosts: localhost
  serial: 1  # Update one at a time
  
  tasks:
    - name: Get current systems
      hawkfish.virtualization.hawkfish_system:
        endpoint: "{{ hawkfish_endpoint }}"
        username: "{{ hawkfish_username }}"
        password: "{{ hawkfish_password }}"
        name: "web-{{ ansible_loop.index }}"
        state: query
      register: current_system

    - name: Create snapshot before update
      hawkfish.virtualization.hawkfish_snapshot:
        endpoint: "{{ hawkfish_endpoint }}"
        username: "{{ hawkfish_username }}"
        password: "{{ hawkfish_password }}"
        system_id: "{{ current_system.system.id }}"
        name: "pre-update-{{ ansible_date_time.epoch }}"
        description: "Snapshot before rolling update"
        state: present

    - name: Insert new OS ISO
      hawkfish.virtualization.hawkfish_media:
        endpoint: "{{ hawkfish_endpoint }}"
        username: "{{ hawkfish_username }}"
        password: "{{ hawkfish_password }}"
        system_id: "{{ current_system.system.id }}"
        image: "{{ new_os_iso_path }}"
        state: inserted

    - name: Set boot to CD for update
      hawkfish.virtualization.hawkfish_system:
        endpoint: "{{ hawkfish_endpoint }}"
        username: "{{ hawkfish_username }}"
        password: "{{ hawkfish_password }}"
        system_id: "{{ current_system.system.id }}"
        boot_override: "Cd"
        boot_persistent: false

    - name: Restart system for update
      hawkfish.virtualization.hawkfish_power:
        endpoint: "{{ hawkfish_endpoint }}"
        username: "{{ hawkfish_username }}"
        password: "{{ hawkfish_password }}"
        system_id: "{{ current_system.system.id }}"
        reset_type: "ForceRestart"
        wait: true

    # Wait for update completion logic here...

    - name: Reset boot to HDD
      hawkfish.virtualization.hawkfish_system:
        endpoint: "{{ hawkfish_endpoint }}"
        username: "{{ hawkfish_username }}"
        password: "{{ hawkfish_password }}"
        system_id: "{{ current_system.system.id }}"
        boot_override: "Hdd"
        boot_persistent: true
```

#### Inventory Management

```yaml
---
- name: Dynamic inventory update
  hosts: localhost
  
  tasks:
    - name: Get all systems
      hawkfish.virtualization.hawkfish_system:
        endpoint: "{{ hawkfish_endpoint }}"
        username: "{{ hawkfish_username }}"
        password: "{{ hawkfish_password }}"
        state: query
      register: all_systems

    - name: Generate inventory
      template:
        src: inventory.j2
        dest: "{{ inventory_output_path }}"
      vars:
        systems: "{{ all_systems.systems }}"

    - name: Update monitoring configuration
      template:
        src: prometheus-targets.j2
        dest: /etc/prometheus/hawkfish-targets.yml
      vars:
        web_servers: "{{ all_systems.systems | selectattr('tags.tier', 'equalto', 'web') | list }}"
      notify: reload prometheus
```

### Module Reference

#### hawkfish_system

```yaml
- name: Manage system
  hawkfish.virtualization.hawkfish_system:
    endpoint: "{{ hawkfish_endpoint }}"
    username: "{{ hawkfish_username }}"
    password: "{{ hawkfish_password }}"
    name: "my-vm"                    # System name
    profile_id: "profile-123"        # Profile to use
    state: present                   # present, absent, query
    tags:                           # System tags
      environment: production
    wait: true                      # Wait for completion
    timeout: 600                    # Timeout in seconds
```

#### hawkfish_power

```yaml
- name: Power control
  hawkfish.virtualization.hawkfish_power:
    endpoint: "{{ hawkfish_endpoint }}"
    username: "{{ hawkfish_username }}"
    password: "{{ hawkfish_password }}"
    system_id: "vm-123"             # System ID
    reset_type: "On"                # On, ForceOff, GracefulShutdown, ForceRestart
    wait: true                      # Wait for state change
    timeout: 300                    # Timeout in seconds
```

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/infrastructure.yml
name: Infrastructure Deployment

on:
  push:
    branches: [main]
    paths: ['terraform/**']

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v4
    
    - name: Setup Terraform
      uses: hashicorp/setup-terraform@v3
      with:
        terraform_version: 1.6.0
    
    - name: Terraform Init
      run: terraform init
      working-directory: terraform/
      env:
        TF_VAR_hawkfish_endpoint: ${{ secrets.HAWKFISH_ENDPOINT }}
        TF_VAR_hawkfish_username: ${{ secrets.HAWKFISH_USERNAME }}
        TF_VAR_hawkfish_password: ${{ secrets.HAWKFISH_PASSWORD }}
    
    - name: Terraform Plan
      run: terraform plan -out=tfplan
      working-directory: terraform/
    
    - name: Terraform Apply
      if: github.ref == 'refs/heads/main'
      run: terraform apply tfplan
      working-directory: terraform/
```

### GitLab CI

```yaml
# .gitlab-ci.yml
stages:
  - validate
  - plan
  - deploy

variables:
  TF_ROOT: terraform/
  TF_STATE_NAME: hawkfish-infrastructure

terraform:validate:
  stage: validate
  image: hashicorp/terraform:1.6
  script:
    - cd $TF_ROOT
    - terraform init -backend=false
    - terraform validate

terraform:plan:
  stage: plan
  image: hashicorp/terraform:1.6
  script:
    - cd $TF_ROOT
    - terraform init
    - terraform plan -out=tfplan
  artifacts:
    paths:
      - $TF_ROOT/tfplan
  only:
    - merge_requests
    - main

terraform:deploy:
  stage: deploy
  image: hashicorp/terraform:1.6
  script:
    - cd $TF_ROOT
    - terraform init
    - terraform apply -auto-approve tfplan
  dependencies:
    - terraform:plan
  only:
    - main
```

### Jenkins Pipeline

```groovy
pipeline {
    agent any
    
    environment {
        HAWKFISH_ENDPOINT = credentials('hawkfish-endpoint')
        HAWKFISH_USERNAME = credentials('hawkfish-username')
        HAWKFISH_PASSWORD = credentials('hawkfish-password')
    }
    
    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }
        
        stage('Terraform Plan') {
            steps {
                dir('terraform') {
                    sh 'terraform init'
                    sh 'terraform plan -out=tfplan'
                }
            }
        }
        
        stage('Approval') {
            when {
                branch 'main'
            }
            steps {
                input message: 'Deploy infrastructure?'
            }
        }
        
        stage('Terraform Apply') {
            when {
                branch 'main'
            }
            steps {
                dir('terraform') {
                    sh 'terraform apply tfplan'
                }
            }
        }
        
        stage('Ansible Configuration') {
            steps {
                ansiblePlaybook(
                    playbook: 'ansible/site.yml',
                    inventory: 'ansible/inventory',
                    credentialsId: 'hawkfish-credentials'
                )
            }
        }
    }
    
    post {
        always {
            archiveArtifacts artifacts: 'terraform/tfplan', allowEmptyArchive: true
        }
        failure {
            emailext subject: 'Infrastructure deployment failed',
                     body: 'The infrastructure deployment pipeline failed.',
                     to: '${DEFAULT_RECIPIENTS}'
        }
    }
}
```

## Monitoring and Alerting

### Prometheus Integration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'hawkfish'
    static_configs:
      - targets: ['hawkfish:8080']
    metrics_path: '/redfish/v1/metrics'
    scrape_interval: 30s
```

### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "HawkFish Infrastructure",
    "panels": [
      {
        "title": "Active Systems",
        "type": "stat",
        "targets": [
          {
            "expr": "hawkfish_systems_total",
            "legendFormat": "Total Systems"
          }
        ]
      },
      {
        "title": "API Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(hawkfish_api_requests_total[5m])",
            "legendFormat": "{{method}} {{path}}"
          }
        ]
      }
    ]
  }
}
```

### Alerting Rules

```yaml
# alerts.yml
groups:
  - name: hawkfish.rules
    rules:
      - alert: HawkFishDown
        expr: up{job="hawkfish"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "HawkFish is down"
          description: "HawkFish has been down for more than 5 minutes"

      - alert: HighAPIErrorRate
        expr: rate(hawkfish_api_requests_total{status=~"5.."}[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High API error rate"
          description: "API error rate is {{ $value }} errors per second"

      - alert: SystemProvisioningFailed
        expr: increase(hawkfish_tasks_total{state="Exception"}[10m]) > 0
        labels:
          severity: warning
        annotations:
          summary: "System provisioning failed"
          description: "{{ $value }} provisioning tasks failed in the last 10 minutes"
```

## Best Practices

### Error Handling

```python
# Robust error handling
async def provision_with_retry(client, profile_id, name, max_retries=3):
    for attempt in range(max_retries):
        try:
            task_id = await client.create_system_from_profile(profile_id, name)
            
            # Wait for completion with timeout
            for _ in range(60):  # 10 minutes max
                task = await client.get_task(task_id)
                if task['TaskState'] == 'Completed':
                    return task['TaskState']
                elif task['TaskState'] == 'Exception':
                    raise Exception(f"Task failed: {task.get('Messages', [])}")
                await asyncio.sleep(10)
            
            raise TimeoutError("Task did not complete within timeout")
            
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
```

### Configuration Management

```python
# Use environment variables and config files
import os
from dataclasses import dataclass

@dataclass
class HawkFishConfig:
    endpoint: str
    username: str
    password: str
    timeout: int = 30
    max_retries: int = 3

def load_config():
    return HawkFishConfig(
        endpoint=os.getenv('HAWKFISH_ENDPOINT', 'http://localhost:8080'),
        username=os.getenv('HAWKFISH_USERNAME', 'admin'),
        password=os.getenv('HAWKFISH_PASSWORD', ''),
        timeout=int(os.getenv('HAWKFISH_TIMEOUT', '30')),
        max_retries=int(os.getenv('HAWKFISH_MAX_RETRIES', '3'))
    )
```

### Security

```bash
# Use secrets management
export HAWKFISH_PASSWORD=$(vault kv get -field=password secret/hawkfish)

# Verify SSL certificates in production
export HAWKFISH_VERIFY_SSL=true

# Use API keys when available
export HAWKFISH_API_KEY=$(vault kv get -field=api_key secret/hawkfish)
```

### Testing

```python
# Mock HawkFish for testing
import pytest
from unittest.mock import AsyncMock

@pytest.fixture
async def mock_hawkfish_client():
    client = AsyncMock()
    client.login.return_value = None
    client.list_systems.return_value = {
        'Members': [{'Id': 'test-vm', 'PowerState': 'Off'}]
    }
    client.power_action.return_value = None
    return client

async def test_bulk_power_on(mock_hawkfish_client):
    # Test bulk power operations
    await bulk_power_control(mock_hawkfish_client)
    mock_hawkfish_client.power_action.assert_called_with('test-vm', 'On')
```
