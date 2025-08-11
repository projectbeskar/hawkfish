# HawkFish Ansible Collection Example

This directory contains example Ansible playbooks for managing HawkFish resources.

## Prerequisites

1. **HawkFish Controller** running at `http://localhost:8080`
2. **Ansible Collection** `hawkfish.virtualization` (to be implemented)

## Collection Modules

The HawkFish Ansible collection would provide these modules:

### `hawkfish_system`
Manage virtual systems (VMs).

```yaml
- name: Create a VM
  hawkfish.virtualization.hawkfish_system:
    endpoint: "http://localhost:8080"
    username: "local"
    password: ""
    name: "my-vm"
    profile_id: "profile-123"
    tags:
      environment: "production"
    state: present
```

### `hawkfish_power`
Manage system power state.

```yaml
- name: Power on VM
  hawkfish.virtualization.hawkfish_power:
    endpoint: "http://localhost:8080"
    username: "local"
    password: ""
    system_id: "vm-123"
    reset_type: "On"
    wait: true
    timeout: 300
```

### `hawkfish_profile`
Manage node profiles.

```yaml
- name: Create VM profile
  hawkfish.virtualization.hawkfish_profile:
    endpoint: "http://localhost:8080"
    username: "local"
    password: ""
    name: "web-server"
    cpu: 4
    memory_mib: 4096
    disk_gib: 50
    network: "default"
    state: present
```

### `hawkfish_media`
Manage virtual media.

```yaml
- name: Insert installation ISO
  hawkfish.virtualization.hawkfish_media:
    endpoint: "http://localhost:8080"
    username: "local"
    password: ""
    system_id: "vm-123"
    image: "/path/to/ubuntu-22.04.iso"
    state: inserted
```

### `hawkfish_subscription`
Manage event subscriptions.

```yaml
- name: Subscribe to power events
  hawkfish.virtualization.hawkfish_subscription:
    endpoint: "http://localhost:8080"
    username: "local"
    password: ""
    destination: "https://webhook.example.com/events"
    event_types:
      - "PowerStateChanged"
    system_ids:
      - "vm-123"
    state: present
```

## Usage

1. **Run the demo playbook**:
   ```bash
   ansible-playbook -i inventory playbook.yml
   ```

2. **With custom variables**:
   ```bash
   ansible-playbook -i inventory playbook.yml \
     -e hawkfish_endpoint=https://hawkfish.example.com \
     -e hawkfish_username=admin \
     -e hawkfish_password=secret
   ```

3. **Cleanup resources**:
   ```bash
   ansible-playbook -i inventory playbook.yml --tags cleanup
   ```

## Collection Structure

The HawkFish Ansible collection would be structured as:

```
collections/
  ansible_collections/
    hawkfish/
      virtualization/
        plugins/
          modules/
            hawkfish_system.py
            hawkfish_power.py
            hawkfish_profile.py
            hawkfish_media.py
            hawkfish_subscription.py
          module_utils/
            hawkfish_client.py
        galaxy.yml
        README.md
```

## Module Parameters

### Common Parameters
All modules would accept these common parameters:

- `endpoint`: HawkFish API endpoint URL
- `username`: Authentication username
- `password`: Authentication password (sensitive)
- `validate_certs`: Validate SSL certificates (default: true)
- `timeout`: Request timeout in seconds (default: 30)

### Error Handling
Modules would handle HawkFish API errors gracefully:

- HTTP errors with proper status codes
- Redfish ExtendedInfo error messages
- Connection timeouts and retries
- Authentication failures

### Idempotency
All modules would be idempotent:

- Check current state before making changes
- Return `changed: false` when no action needed
- Support `check_mode` for dry-run testing

## Examples

### Basic VM Lifecycle
```yaml
- name: Create and start a VM
  block:
    - name: Create VM profile
      hawkfish.virtualization.hawkfish_profile:
        name: "standard"
        cpu: 2
        memory_mib: 2048
        disk_gib: 20
        state: present
      register: profile

    - name: Create VM
      hawkfish.virtualization.hawkfish_system:
        name: "test-vm"
        profile_id: "{{ profile.profile.id }}"
        state: present
      register: vm

    - name: Power on VM
      hawkfish.virtualization.hawkfish_power:
        system_id: "{{ vm.system.id }}"
        reset_type: "On"
        wait: true
```

### Bulk Operations
```yaml
- name: Create multiple VMs
  hawkfish.virtualization.hawkfish_system:
    name: "vm-{{ item }}"
    profile_id: "{{ standard_profile.id }}"
    state: present
  loop: "{{ range(1, 11) | list }}"  # Creates vm-1 through vm-10
```

## Collection Development

To implement the HawkFish Ansible collection:

1. Create module skeleton with argument specs
2. Implement HawkFish API client in `module_utils`
3. Add proper error handling and return values
4. Write comprehensive tests
5. Package as Galaxy collection
