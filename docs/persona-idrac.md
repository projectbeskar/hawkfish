# Dell iDRAC Persona

The Dell iDRAC persona provides Dell iDRAC9-compatible Redfish endpoints for testing and migration scenarios. This persona maps Dell-specific API endpoints to HawkFish core functionality while maintaining clear compatibility disclaimers.

## 🚨 **Important Disclaimers**

- **NOT GENUINE DELL SOFTWARE**: This is HawkFish compatibility mode for testing only
- **NO DELL AFFILIATION**: HawkFish is not affiliated with or endorsed by Dell Technologies
- **TRADEMARKS**: Dell, iDRAC, and PowerEdge are trademarks of Dell Technologies
- **SUPPORT**: Contact HawkFish maintainers, not Dell, for support with compatibility features

## Activation

### Project-Level Default

```bash
# Set default persona for a project
hawkfish projects set-persona my-project dell_idrac9
```

### System-Level Override

```bash
# Set persona for specific system
hawkfish persona set vm-001 dell_idrac9

# Or via API
curl -X PATCH https://localhost:8080/redfish/v1/Oem/HawkFish/Personas/Systems/vm-001 \
  -H "X-Auth-Token: $TOKEN" \
  -d '{"persona": "dell_idrac9"}'
```

## Supported Endpoints

### Manager Identity

```http
GET /redfish/v1/Managers/iDRAC.Embedded.1
```

Returns Dell iDRAC9 Manager identity with:
- **Manufacturer**: "HawkFish (Dell iDRAC-compatible mode)"
- **Model**: "Integrated Dell Remote Access Controller 9"
- **ManagerType**: "BMC"
- **Dell OEM data**: DellManager type and version info
- **Compatibility disclaimer**: Clear identification as compatibility mode

```json
{
  "@odata.type": "#Manager.v1_10_0.Manager",
  "@odata.id": "/redfish/v1/Managers/iDRAC.Embedded.1",
  "Id": "iDRAC.Embedded.1",
  "ManagerType": "BMC",
  "Manufacturer": "HawkFish (Dell iDRAC-compatible mode)",
  "Model": "Integrated Dell Remote Access Controller 9",
  "FirmwareVersion": "HawkFish-0.9.0-idrac9",
  "Oem": {
    "Dell": {
      "DellManager": {
        "DellManagerType": "iDRAC",
        "iDRACVersion": "4.40.00.00"
      }
    },
    "HawkFish": {
      "CompatibilityDisclaimer": "HawkFish Dell iDRAC compatibility mode for testing; not affiliated with Dell."
    }
  }
}
```

### VirtualMedia Operations

#### Collection

```http
GET /redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia
```

#### CD Resource

```http
GET /redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD
```

Exposes Dell-specific VirtualMedia actions:
- `Oem.DellVirtualMedia.InsertVirtualMedia`
- `Oem.DellVirtualMedia.EjectVirtualMedia`

#### Insert Media

```http
POST /redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/Oem/DellVirtualMedia.InsertVirtualMedia
```

**Request Body:**
```json
{
  "SystemId": "vm-001",
  "Image": "http://example.com/ubuntu-22.04.iso"
}
```

**Response:**
```json
{
  "TaskState": "Completed",
  "Oem": {
    "Dell": {
      "JobStatus": "Completed"
    },
    "HawkFish": {
      "CompatibilityDisclaimer": "HawkFish Dell iDRAC compatibility mode for testing; not affiliated with Dell."
    }
  }
}
```

#### Eject Media

```http
POST /redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/Oem/DellVirtualMedia.EjectVirtualMedia
```

**Request Body:**
```json
{
  "SystemId": "vm-001"
}
```

### Jobs/Queue Integration

#### Jobs Collection

```http
GET /redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs
```

Maps HawkFish TaskService to Dell Job semantics:

```json
{
  "@odata.type": "#DellJobCollection.DellJobCollection",
  "@odata.id": "/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs",
  "Name": "Dell Job Queue",
  "Members": [
    {
      "@odata.id": "/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/job-123"
    }
  ],
  "Members@odata.count": 1
}
```

#### Individual Job

```http
GET /redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs/{job_id}
```

**Dell Job Format:**
```json
{
  "@odata.type": "#DellJob.v1_0_0.DellJob",
  "Id": "job-123",
  "Name": "Migrate vm-001",
  "JobState": "Completed",
  "PercentComplete": 100,
  "StartTime": "2025-01-15T10:30:00Z",
  "EndTime": "2025-01-15T10:32:15Z",
  "Message": "Migration completed successfully",
  "JobType": "Configuration"
}
```

### BIOS Configuration

#### Current Settings

```http
GET /redfish/v1/Systems/{system_id}/Bios
```

Dell-enhanced response with BIOSConfig OEM data:

```json
{
  "@odata.type": "#Bios.v1_1_0.Bios",
  "Id": "BIOS",
  "AttributeRegistry": "DellBiosAttributeRegistry.v1_0_0",
  "Attributes": {
    "BootMode": "Uefi",
    "PersistentBootConfigOrder": ["Hdd", "Cd", "Pxe"]
  },
  "Oem": {
    "Dell": {
      "BIOSConfig": {
        "PendingChanges": false
      }
    },
    "HawkFish": {
      "CompatibilityDisclaimer": "HawkFish Dell iDRAC compatibility mode for testing; not affiliated with Dell."
    }
  }
}
```

#### Configure Settings

```http
PATCH /redfish/v1/Systems/{system_id}/Bios/Settings
```

**Request with Dell ApplyTime:**
```json
{
  "Attributes": {
    "BootMode": "Uefi",
    "PersistentBootConfigOrder": ["Cd", "Pxe", "Hdd"]
  },
  "Oem": {
    "Dell": {
      "ApplyTime": "OnReset"
    }
  }
}
```

**Response:**
```json
{
  "TaskState": "Pending",
  "Message": "BIOS settings will be applied onreset",
  "Oem": {
    "Dell": {
      "ApplyTime": "OnReset",
      "BIOSConfig": {
        "JobType": "BIOSConfiguration"
      }
    },
    "HawkFish": {
      "CompatibilityDisclaimer": "HawkFish Dell iDRAC compatibility mode for testing; not affiliated with Dell."
    }
  }
}
```

## Supported BIOS Attributes

| Attribute | Values | ApplyTime | Notes |
|-----------|---------|-----------|--------|
| `BootMode` | `Uefi`, `Bios` | OnReset | Firmware mode selection |
| `PersistentBootConfigOrder` | Array of `["Cd","Pxe","Hdd"]` | OnReset/Immediate | Boot device priority |

## Event Adaptation

Core HawkFish events are adapted to include Dell-specific formatting:

### Event Structure

```json
{
  "EventType": "PowerStateChanged",
  "systemId": "vm-001",
  "Oem": {
    "Dell": {
      "EventID": "dell_PowerStateChanged_a1b2c3d4",
      "Category": "System",
      "Source": "iDRAC",
      "Severity": "OK"
    },
    "HawkFish": {
      "CompatibilityDisclaimer": "HawkFish Dell iDRAC compatibility mode for testing; not affiliated with Dell."
    }
  }
}
```

### Event Categories

| HawkFish Event | Dell Category | Purpose |
|----------------|---------------|---------|
| `PowerStateChanged` | System | Power state transitions |
| `MediaInserted` | VirtualMedia | Virtual media operations |
| `MediaEjected` | VirtualMedia | Virtual media operations |
| `BiosSettingsApplied` | BIOS | BIOS configuration changes |
| `SystemCreated` | System | System lifecycle |
| `SystemDeleted` | System | System lifecycle |

## Error Handling

Dell iDRAC persona provides Dell-compatible error messages:

### Example Error Response

```json
{
  "error": {
    "code": "Oem.Dell.BIOS.InvalidAttribute",
    "message": "The BIOS attribute 'BootMode' has an invalid value 'InvalidMode'",
    "@Message.ExtendedInfo": [{
      "MessageId": "Oem.Dell.BIOS.InvalidAttribute",
      "Message": "Invalid BIOS attribute: BootMode=InvalidMode",
      "Severity": "Warning",
      "Resolution": "Check BIOS attribute values and system state."
    }]
  }
}
```

### Dell Message Registry

| Message ID | Purpose | Arguments |
|------------|---------|-----------|
| `Oem.Dell.BIOS.InvalidAttribute` | Invalid BIOS value | attribute, value |
| `Oem.Dell.BIOS.RequiresPowerOff` | ApplyTime validation | none |
| `Oem.Dell.Media.DeviceUnavailable` | Media device error | device |

## CLI Integration

### Basic Operations

```bash
# Set Dell persona
hawkfish persona set vm-001 dell_idrac9

# Show BIOS settings
hawkfish bios show vm-001

# Configure BIOS
hawkfish bios set vm-001 \
  --boot-mode uefi \
  --boot-order Cd,Pxe,Hdd \
  --apply-time onreset

# Reset to apply BIOS changes
hawkfish power reset vm-001
```

### Media Operations

```bash
# Insert ISO
hawkfish media insert vm-001 http://example.com/ubuntu.iso

# Eject media
hawkfish media eject vm-001
```

## Examples

### Shell Script

Use the provided example script for complete workflow testing:

```bash
export HAWKFISH_URL="https://your-hawkfish:8080"
export HAWKFISH_TOKEN="your-token"
export SYSTEM_ID="vm-001"

./examples/idrac/idrac_virtual_media_example.sh
```

### Python Integration

```python
import httpx

# Configure Dell persona
async def set_dell_persona(base_url: str, token: str, system_id: str):
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.patch(
            f"{base_url}/redfish/v1/Oem/HawkFish/Personas/Systems/{system_id}",
            headers={"X-Auth-Token": token},
            json={"persona": "dell_idrac9"}
        )
        return response.status_code == 200

# Insert media via Dell endpoint  
async def insert_media_dell(base_url: str, token: str, system_id: str, iso_url: str):
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.post(
            f"{base_url}/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/Oem/DellVirtualMedia.InsertVirtualMedia",
            headers={"X-Auth-Token": token},
            json={"SystemId": system_id, "Image": iso_url}
        )
        return response.json()
```

## Testing

### Interoperability Tests

Enable Dell iDRAC persona testing:

```bash
export HF_TEST_PERSONA=dell_idrac9
pytest tests/interop/idrac/ -v
```

### Manual Verification

1. **Manager Identity**: Verify Dell branding and disclaimers
2. **VirtualMedia Flow**: Insert → Verify → Eject cycle
3. **Jobs Integration**: Check TaskService mapping
4. **BIOS Configuration**: Test attribute validation and staging
5. **Error Handling**: Verify Dell message IDs in responses

## Coverage Matrix

### Endpoint Support

| Category | Endpoints | Methods | Status |
|----------|-----------|---------|---------|
| Manager Identity | 1 | GET | ✅ Complete |
| VirtualMedia | 3 | GET, POST | ✅ Complete |
| Jobs/Queue | 2 | GET | ✅ Complete |
| BIOS Configuration | 2 | GET, PATCH | ✅ Complete |
| **Total** | **8** | **Mixed** | ✅ **100%** |

### Feature Comparison

| Feature | HPE iLO5 Persona | Dell iDRAC9 Persona |
|---------|------------------|---------------------|
| Manager Identity | ✅ iLO.Embedded.1 | ✅ iDRAC.Embedded.1 |
| VirtualMedia | ✅ Full support | ✅ Full support |
| Console Sessions | ✅ LaunchConsole | ❌ Not implemented |
| Jobs/Tasks | ✅ HPE Jobs format | ✅ Dell Jobs format |
| BIOS Management | ✅ 3 attributes | ✅ 2 attributes |
| SecureBoot | ✅ Supported | ❌ Not implemented |
| Message Registry | ✅ 8 messages | ✅ 3 messages |

## Limitations

### Current Implementation

- **Simplified BIOS**: Only BootMode and PersistentBootConfigOrder supported
- **No SecureBoot**: SecureBoot attribute not implemented in Dell persona
- **No Console**: Console session management not implemented
- **Job Mapping**: Basic TaskService mapping without Dell-specific job types

### Future Enhancements

- Additional BIOS attributes (PCI settings, memory configuration)
- Console session support via Dell Remote Console format
- Enhanced job types and queue management
- Storage configuration endpoints
- Network configuration support

## Security Considerations

1. **Admin-Only Persona Changes**: Prevents unauthorized vendor switching
2. **Clear Disclaimers**: Every response includes compatibility notice
3. **No Credential Handling**: Uses HawkFish authentication exclusively
4. **Audit Logging**: All operations logged with persona context

## Migration Scenarios

### From Real Dell iDRAC

1. **Assessment**: Use Dell endpoints to verify compatibility
2. **Testing**: Validate workflows with actual tools/scripts
3. **Migration**: Point tools to HawkFish with Dell persona enabled
4. **Validation**: Compare results and adjust workflows

### Tool Compatibility

The Dell iDRAC persona is designed to work with:
- Dell OpenManage tools (limited compatibility)
- Custom scripts using Dell Redfish endpoints
- Third-party management platforms expecting iDRAC APIs
- Migration and testing frameworks

## Best Practices

1. **Environment Separation**: Use Dell persona in dedicated test/dev environments
2. **Disclaimer Awareness**: Always verify compatibility disclaimer in responses
3. **Feature Validation**: Test specific features before production use
4. **Fallback Planning**: Maintain access to standard HawkFish endpoints
5. **Documentation**: Document any workflow differences discovered during testing

---

**Remember**: This is a compatibility layer for testing and migration purposes. Always include proper disclaimers and maintain clear boundaries between compatibility mode and production Dell systems.
