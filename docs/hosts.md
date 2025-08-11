### Host Pools

HawkFish supports managing multiple libvirt hosts for distributed VM placement.

#### API Endpoints

- `GET /redfish/v1/Oem/HawkFish/Hosts` - List all hosts
- `POST /redfish/v1/Oem/HawkFish/Hosts` - Add a new host
- `GET /redfish/v1/Oem/HawkFish/Hosts/{id}` - Get host details
- `DELETE /redfish/v1/Oem/HawkFish/Hosts/{id}` - Remove a host

#### Host Schema

```json
{
  "URI": "qemu+ssh://user@host/system",
  "Name": "production-host-1",
  "Labels": {
    "environment": "production",
    "ssd": "true"
  }
}
```

#### Placement Algorithm

When creating VMs, HawkFish automatically selects hosts based on:
1. Resource availability (CPU/memory fit)
2. Label constraints (if specified in NodeSpec)
3. Spread algorithm (least allocated vCPUs)

#### CLI Usage

```bash
# List hosts
hawkfish hosts

# Add a host
hawkfish host-add qemu+ssh://user@host/system "Host 1" --labels environment=prod,ssd=true

# Remove a host
hawkfish host-rm <host-id>
```
