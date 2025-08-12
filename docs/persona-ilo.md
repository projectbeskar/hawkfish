# HPE iLO Persona Compatibility Mode

HawkFish includes an HPE iLO5 persona that provides vendor-compatible endpoints for testing and migration scenarios. This compatibility mode maps HPE-specific API endpoints to HawkFish core functionality while maintaining clear disclaimers.

## ⚠️ Important Disclaimers

- **Not Genuine HPE Software**: This is a compatibility layer for testing purposes only
- **No HPE Affiliation**: HawkFish is not affiliated with or endorsed by HPE
- **Testing Use Only**: Intended for lab environments and migration testing
- **Clear Identification**: All responses include compatibility disclaimers

## Persona Architecture

### Persona Selection

HawkFish supports multiple personas (vendor compatibility modes):

1. **Project Default**: Set via `Oem.HawkFish.DefaultPersona` in project settings
2. **System Override**: Per-system persona via `Systems/{id}/Oem/HawkFish/Persona`
3. **Fallback**: "generic" standard Redfish implementation

### RBAC Controls

- **View Personas**: All authenticated users
- **Change System Persona**: Project admins only
- **Change Project Default**: Project admins only

## HPE iLO5 Endpoints

### Manager Resource (iLO Identity)

```http
GET /redfish/v1/Managers/iLO.Embedded.1
```

**Response:**
```json
{
  "@odata.type": "#Manager.v1_10_0.Manager",
  "@odata.id": "/redfish/v1/Managers/iLO.Embedded.1",
  "Id": "iLO.Embedded.1",
  "Name": "Manager",
  "ManagerType": "BMC",
  "Manufacturer": "HawkFish (HPE iLO-compatible mode)",
  "Model": "Integrated Lights-Out 5",
  "FirmwareVersion": "HawkFish-0.8.0-ilo5",
  "Status": {
    "State": "Enabled", 
    "Health": "OK"
  },
  "Links": {
    "VirtualMedia": {
      "@odata.id": "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia"
    }
  },
  "Oem": {
    "HawkFish": {
      "CompatibilityDisclaimer": "HawkFish HPE iLO compatibility mode for testing; not affiliated with HPE."
    }
  }
}
```

### Virtual Media Aliases

#### Collection
```http
GET /redfish/v1/Managers/iLO.Embedded.1/VirtualMedia
```

#### CD Resource
```http
GET /redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1
```

#### Insert Media (HPE Format)
```http
POST /redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1/Actions/VirtualMedia.InsertMedia
```

**Body:**
```json
{
  "SystemId": "vm-001",
  "Image": "http://example.com/ubuntu-22.04.iso"
}
```

#### Eject Media (HPE Format) 
```http
POST /redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1/Actions/VirtualMedia.EjectMedia
```

**Body:**
```json
{
  "SystemId": "vm-001"
}
```

### Jobs Mapping

```http
GET /redfish/v1/Managers/iLO.Embedded.1/Oem/Hpe/Jobs
```

Maps to HawkFish TaskService with HPE-compatible format.

## BIOS/UEFI Settings

### Supported Attributes

| Attribute | Values | Description |
|-----------|--------|-------------|
| `BootMode` | `Uefi`, `LegacyBios` | Firmware type (OVMF vs SeaBIOS) |
| `SecureBoot` | `Enabled`, `Disabled` | Secure Boot (UEFI only) |
| `PersistentBootConfigOrder` | `["Cd","Pxe","Hdd"]` | Boot device priority |

### Get BIOS Settings

```http
GET /redfish/v1/Systems/{systemId}/Bios
```

**Response:**
```json
{
  "@odata.type": "#Bios.v1_1_0.Bios",
  "@odata.id": "/redfish/v1/Systems/vm-001/Bios",
  "Id": "BIOS",
  "Name": "BIOS Configuration Current Settings",
  "Attributes": {
    "BootMode": "Uefi",
    "SecureBoot": "Disabled",
    "PersistentBootConfigOrder": ["Hdd", "Cd", "Pxe"]
  },
  "Links": {
    "Settings": {
      "@odata.id": "/redfish/v1/Systems/vm-001/Bios/Settings"
    }
  },
  "Oem": {
    "Hpe": {
      "PendingChanges": false
    },
    "HawkFish": {
      "CompatibilityDisclaimer": "HawkFish HPE iLO compatibility mode for testing; not affiliated with HPE."
    }
  }
}
```

### Update BIOS Settings

```http
PATCH /redfish/v1/Systems/{systemId}/Bios/Settings
```

**Body:**
```json
{
  "Attributes": {
    "BootMode": "Uefi",
    "SecureBoot": "Enabled",
    "PersistentBootConfigOrder": ["Cd", "Pxe", "Hdd"]
  },
  "Oem": {
    "Hpe": {
      "ApplyTime": "OnReset"
    }
  }
}
```

### ApplyTime Behavior

- **OnReset**: Changes staged and applied on next `ComputerSystem.Reset`
- **Immediate**: Apply now (only if no reboot required and system powered off)

### BIOS Implementation Mapping

| HPE Concept | HawkFish Implementation |
|-------------|------------------------|
| BootMode=Uefi | Libvirt OVMF firmware |
| BootMode=LegacyBios | Libvirt SeaBIOS firmware |
| SecureBoot=Enabled | OVMF secure boot varstore |
| SecureBoot=Disabled | OVMF non-secure varstore |
| PersistentBootConfigOrder | Libvirt device boot priority |

## Event Adaptation

Events in HPE persona include additional OEM fields:

```json
{
  "EventType": "PowerStateChanged",
  "systemId": "vm-001",
  "Oem": {
    "Hpe": {
      "EventID": "hpe_PowerStateChanged_a1b2c3d4",
      "Category": "Power",
      "Severity": "OK"
    },
    "HawkFish": {
      "CompatibilityDisclaimer": "HawkFish HPE iLO compatibility mode for testing; not affiliated with HPE."
    }
  }
}
```

### Event Category Mapping

| HawkFish Event | HPE Category |
|----------------|--------------|
| PowerStateChanged | Power |
| MediaInserted/Ejected | VirtualMedia |
| BiosSettingsApplied | BIOS |
| SystemCreated/Deleted | System |
| Others | General |

## Error Messages

HPE persona provides vendor-specific error messages:

```json
{
  "error": {
    "code": "Oem.Hpe.Bios.RequiresPowerOff",
    "message": "The requested BIOS changes require the system to be powered off.",
    "@Message.ExtendedInfo": [{
      "MessageId": "Oem.Hpe.Bios.RequiresPowerOff",
      "Message": "The requested BIOS setting changes require ApplyTime=OnReset or system power off.",
      "Resolution": "Set ApplyTime to OnReset or power off the system before applying changes.",
      "Severity": "Warning"
    }]
  }
}
```

### Message Registry

- `Oem.Hpe.Bios.InvalidAttribute`: Invalid BIOS attribute value
- `Oem.Hpe.Bios.RequiresPowerOff`: Change requires system power off
- `Oem.Hpe.Bios.RequiresUefiForSecureBoot`: SecureBoot requires UEFI mode
- `Oem.Hpe.Media.DeviceUnavailable`: Virtual media device unavailable

## CLI Usage

### Persona Management

```bash
# List available personas
hawkfish persona list

# Show current persona for a system
hawkfish persona show vm-001

# Set HPE iLO5 persona for a system (admin only)
hawkfish persona set vm-001 hpe_ilo5
```

### BIOS Management

```bash
# Show BIOS settings
hawkfish bios show vm-001

# Set BIOS attributes (applied on reset)
hawkfish bios set vm-001 \
  --boot-mode uefi \
  --secure-boot enabled \
  --boot-order cd,pxe,hdd \
  --apply-time onreset

# Apply immediately (if supported)
hawkfish bios set vm-001 \
  --boot-mode uefi \
  --apply-time immediate
```

## Example Workflows

### 1. HPE Tool Migration Testing

```bash
# Set system to HPE persona
hawkfish persona set server01 hpe_ilo5

# Configure BIOS for secure boot
hawkfish bios set server01 --boot-mode uefi --secure-boot enabled

# Insert installation media via HPE endpoint
curl -X POST "https://hawkfish:8080/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1/Actions/VirtualMedia.InsertMedia" \
  -H "X-Auth-Token: $TOKEN" \
  -d '{"SystemId": "server01", "Image": "http://repo.local/rhel9.iso"}'

# Power on with CD boot
hawkfish power server01 on
```

### 2. BIOS Configuration Staging

```bash
# Stage BIOS changes for multiple systems
for system in server01 server02 server03; do
  hawkfish bios set $system \
    --boot-mode uefi \
    --secure-boot enabled \
    --boot-order cd,pxe,hdd \
    --apply-time onreset
done

# Power cycle to apply changes
for system in server01 server02 server03; do
  hawkfish power $system forcerestart
done
```

### 3. Event Monitoring

```bash
# Subscribe to events with HPE format
hawkfish events subscribe \
  --url https://monitoring.local/webhook \
  --types PowerStateChanged,BiosSettingsApplied \
  --secret mysecret
```

## Limitations

### Current Implementation

- **Mock BIOS Changes**: Actual libvirt firmware switching not implemented
- **Simplified SecureBoot**: OVMF varstore management needs integration
- **Limited Jobs**: Basic TaskService mapping only

### Future Enhancements

- Full libvirt firmware integration
- OVMF secure boot varstore management  
- Enhanced job progress mapping
- Additional BIOS attributes
- Boot order enforcement

## Security Considerations

1. **Admin-Only Persona Changes**: Prevents privilege escalation
2. **Clear Disclaimers**: Maintains transparency about compatibility mode
3. **No Trademark Misuse**: Avoids trademark violations
4. **Audit Logging**: All persona/BIOS changes logged

## Configuration

### Environment Variables

```bash
# Enable persona system (enabled by default)
HF_PERSONA_ENABLED=true

# Default project persona  
HF_DEFAULT_PERSONA=generic
```

### Project Settings

```json
{
  "project_id": "lab",
  "default_persona": "hpe_ilo5"
}
```

This allows organizations to test HPE-specific tooling and workflows against HawkFish while maintaining clear boundaries and disclaimers about the compatibility layer nature.
