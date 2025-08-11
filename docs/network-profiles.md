### Network Profiles

Template network configurations for VM deployment.

#### API Endpoints

- `GET /redfish/v1/Oem/HawkFish/NetworkProfiles` - List all network profiles
- `POST /redfish/v1/Oem/HawkFish/NetworkProfiles` - Create a new profile
- `GET /redfish/v1/Oem/HawkFish/NetworkProfiles/{id}` - Get profile details
- `DELETE /redfish/v1/Oem/HawkFish/NetworkProfiles/{id}` - Remove a profile

#### Network Profile Schema

```json
{
  "Name": "production-network",
  "LibvirtNetwork": "default",
  "Bridge": null,
  "VLAN": 100,
  "MACPolicy": "auto",
  "CountPerSystem": 2,
  "CloudInitNetwork": {
    "ethernets": {
      "eth0": {
        "dhcp4": true
      },
      "eth1": {
        "addresses": ["192.168.1.{system_name}/24"]
      }
    }
  },
  "Labels": {
    "environment": "production"
  }
}
```

#### Features

- **Multiple NICs**: `CountPerSystem` specifies how many NICs to attach
- **Network Types**: Support for libvirt networks or bridge devices
- **VLAN Support**: Optional VLAN tagging
- **MAC Policy**: Auto-generated or fixed MAC addresses
- **Cloud-Init Integration**: Generate network-config with template expansion
- **Template Variables**: `{system_name}` is replaced with actual system name

#### CLI Usage

```bash
# List network profiles
hawkfish netprofiles

# Create a profile
hawkfish netprofile-create production --libvirt-network default --vlan 100 --count 2

# Remove a profile
hawkfish netprofile-rm <profile-id>
```
