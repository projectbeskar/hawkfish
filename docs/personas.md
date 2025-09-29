# Persona System

The HawkFish Persona System provides vendor-specific hardware compatibility, allowing HawkFish to emulate the behavior and API endpoints of specific hardware platforms like HPE iLO and Dell iDRAC.

## Overview

Personas enable HawkFish to present familiar interfaces to existing tools and workflows designed for specific hardware vendors. This compatibility layer translates between standard Redfish operations and vendor-specific expectations.

### Supported Personas

- **Generic Redfish** (default) - Standard DMTF Redfish implementation
- **HPE iLO 5** - HPE Integrated Lights-Out compatibility
- **Dell iDRAC 9** - Dell Integrated Dell Remote Access Controller compatibility

## Architecture

### Persona Components

```
┌─────────────────────────────────────────────────────────────────┐
│                      Client Request                            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Persona Registry                             │
├─────────────────────────────────────────────────────────────────┤
│  • Route Detection      • Plugin Loading   • Compatibility     │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Active Persona                              │
├─────────────────────────────────────────────────────────────────┤
│  • Endpoint Mapping    • Event Adaptation  • Error Translation │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Core HawkFish Services                       │
└─────────────────────────────────────────────────────────────────┘
```

### Persona Features

#### Endpoint Aliasing
Map vendor-specific endpoints to HawkFish functionality:
```
HPE iLO:  /redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1
Dell:     /redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD
Generic:  /redfish/v1/Systems/{id}/VirtualMedia/Cd
```

#### Event Adaptation
Transform core events into vendor-specific formats:
```python
# Core HawkFish event
{
    "EventType": "PowerStateChanged",
    "SystemId": "vm-001",
    "NewState": "On"
}

# HPE iLO adapted event
{
    "EventType": "StatusChange",
    "Oem": {
        "Hpe": {
            "EventID": "iLO.2.14.ServerPowerOn",
            "Category": "System"
        }
    }
}
```

#### Error Message Translation
Provide vendor-specific error messages and resolution guidance:
```python
# Core error
{
    "@Message.MessageId": "InvalidAttribute",
    "Message": "Invalid BIOS setting"
}

# HPE adapted error
{
    "@Message.MessageId": "iLO.2.14.InvalidBiosAttribute",
    "Oem": {
        "Hpe": {
            "MessageRegistry": "iLO",
            "Resolution": "Verify attribute name and value range"
        }
    }
}
```

## Configuration

### Setting System Persona

#### Via CLI
```bash
# Set HPE iLO persona for a system
hawkfish persona set web-01 hpe_ilo5

# Set Dell iDRAC persona
hawkfish persona set web-01 dell_idrac9

# Reset to generic Redfish
hawkfish persona set web-01 generic

# View current persona
hawkfish persona show web-01
```

#### Via API
```bash
curl -X PATCH "$HAWKFISH_URL/redfish/v1/Systems/web-01" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Oem": {
      "HawkFish": {
        "Persona": "hpe_ilo5"
      }
    }
  }'
```

### Global Persona Configuration

Set default persona for new systems:

```bash
# Environment variable
export HF_DEFAULT_PERSONA=hpe_ilo5

# Configuration file
echo "default_persona: hpe_ilo5" >> ~/.hawkfish/config.yaml

# CLI global setting
hawkfish config set default-persona hpe_ilo5
```

### Persona Auto-Detection

HawkFish can auto-detect persona based on client behavior:

```bash
# Enable auto-detection
hawkfish config set persona-auto-detect true

# Configure detection rules
hawkfish persona-rules add \
  --pattern "/redfish/v1/Managers/iLO.*" \
  --persona hpe_ilo5

hawkfish persona-rules add \
  --pattern "/redfish/v1/Managers/iDRAC.*" \
  --persona dell_idrac9
```

## HPE iLO Integration

### Supported Features

#### Manager Identity
- **Endpoint**: `/redfish/v1/Managers/iLO.Embedded.1`
- **Features**: Manager information, firmware version, network settings
- **Compatibility**: iLO 5 behavior and responses

#### Virtual Media
- **Endpoints**: 
  - `/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia`
  - `/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1`
- **Operations**: Insert, eject, status check
- **Media Types**: CD/DVD, USB, floppy

#### BIOS Configuration
- **Endpoint**: `/redfish/v1/Systems/{id}/Bios`
- **Features**: Attribute staging, ApplyTime support, pending changes
- **iLO-specific**: HPE BIOS attributes and validation

#### Console Access
- **Endpoint**: `/redfish/v1/Managers/iLO.Embedded.1/RemoteConsole`
- **Protocols**: HTML5 console (WebSocket), VNC
- **Security**: One-time tokens, session management

#### Jobs and Tasks
- **Endpoint**: `/redfish/v1/Managers/iLO.Embedded.1/Oem/Hpe/Jobs`
- **Features**: Job queue, status tracking, completion events
- **Integration**: Maps to HawkFish task system

### HPE iLO Example Usage

#### Basic Manager Operations
```bash
# Get iLO manager information
curl "$HAWKFISH_URL/redfish/v1/Managers/iLO.Embedded.1" \
  -H "X-Auth-Token: $TOKEN"

# Response includes HPE-specific properties
{
  "@odata.type": "#Manager.v1_5_0.Manager",
  "Id": "iLO.Embedded.1",
  "Name": "Manager",
  "ManagerType": "BMC",
  "FirmwareVersion": "2.44",
  "Oem": {
    "Hpe": {
      "Type": "iLO 5",
      "License": {
        "LicenseType": "Evaluation"
      }
    },
    "HawkFish": {
      "CompatibilityDisclaimer": "This is a virtual iLO implementation..."
    }
  }
}
```

#### Virtual Media Operations
```bash
# Insert Ubuntu ISO via iLO endpoint
curl -X POST "$HAWKFISH_URL/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1/Actions/VirtualMedia.InsertMedia" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "SystemId": "web-01",
    "Image": "http://images.local/ubuntu-22.04.iso"
  }'
```

#### BIOS Configuration
```bash
# Stage BIOS changes with HPE ApplyTime
curl -X PATCH "$HAWKFISH_URL/redfish/v1/Systems/web-01/Bios/Settings" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "Attributes": {
      "BootMode": "Uefi",
      "SecureBoot": "Enabled"
    },
    "Oem": {
      "Hpe": {
        "ApplyTime": "OnReset"
      }
    }
  }'
```

## Dell iDRAC Integration

### Supported Features

#### Manager Identity
- **Endpoint**: `/redfish/v1/Managers/iDRAC.Embedded.1`
- **Features**: iDRAC information, lifecycle controller, system inventory
- **Compatibility**: iDRAC 9 behavior and responses

#### Virtual Media
- **Endpoints**:
  - `/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia`
  - `/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD`
- **Operations**: Mount, unmount, boot from virtual media
- **Integration**: Dell-specific media handling

#### Jobs System
- **Endpoint**: `/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs`
- **Features**: Job queue management, scheduling, dependencies
- **Types**: Configuration, firmware update, diagnostic jobs

#### System Configuration
- **Endpoints**: Dell-specific configuration endpoints
- **Features**: BIOS, RAID, network configuration
- **Validation**: Dell hardware constraint validation

### Dell iDRAC Example Usage

#### Manager Information
```bash
# Get iDRAC manager details
curl "$HAWKFISH_URL/redfish/v1/Managers/iDRAC.Embedded.1" \
  -H "X-Auth-Token: $TOKEN"

# Response includes Dell-specific properties
{
  "@odata.type": "#Manager.v1_5_0.Manager",
  "Id": "iDRAC.Embedded.1",
  "Name": "Manager",
  "ManagerType": "BMC",
  "FirmwareVersion": "4.40.10.00",
  "Oem": {
    "Dell": {
      "ProductInfo": {
        "ProductName": "Integrated Dell Remote Access Controller"
      },
      "ServiceTag": "VIRTUAL01"
    }
  }
}
```

#### Job Management
```bash
# Create BIOS configuration job
curl -X POST "$HAWKFISH_URL/redfish/v1/Managers/iDRAC.Embedded.1/Oem/Dell/Jobs" \
  -H "X-Auth-Token: $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "JobType": "BIOSConfiguration",
    "SystemId": "web-01",
    "ScheduledStartTime": "TIME_NOW",
    "UntilTime": "20991231235959"
  }'
```

## Custom Persona Development

### Creating a Custom Persona

#### 1. Define Persona Plugin
```python
# custom_persona.py
from hawkfish_controller.persona.base import PersonaPlugin

class CustomHardwarePersona(PersonaPlugin):
    name = "custom_hardware"
    vendor = "Custom Vendor"
    model = "Hardware Model"
    
    def get_manager_endpoint(self) -> str:
        return "/redfish/v1/Managers/CustomBMC.1"
    
    def adapt_event(self, core_event: dict) -> list[dict]:
        adapted = core_event.copy()
        adapted["Oem"] = {
            "CustomVendor": {
                "EventCategory": self._map_event_category(core_event["EventType"]),
                "Timestamp": core_event.get("timestamp", "")
            }
        }
        return [adapted]
    
    def adapt_error(self, core_error: dict) -> dict:
        adapted = core_error.copy()
        adapted["Oem"] = {
            "CustomVendor": {
                "ErrorCode": self._map_error_code(core_error["@Message.MessageId"]),
                "Resolution": self._get_resolution(core_error)
            }
        }
        return adapted

# Register the plugin
custom_persona_plugin = CustomHardwarePersona()
```

#### 2. Register the Persona
```python
# In your application startup
from hawkfish_controller.persona.registry import persona_registry

persona_registry.register_plugin(custom_persona_plugin)
```

#### 3. Configuration
```bash
# Use your custom persona
hawkfish persona set web-01 custom_hardware
```

### Persona Testing

#### Unit Testing
```python
# test_custom_persona.py
import pytest
from your_module import custom_persona_plugin

def test_event_adaptation():
    core_event = {
        "EventType": "PowerStateChanged",
        "SystemId": "test-system",
        "NewState": "On"
    }
    
    adapted_events = custom_persona_plugin.adapt_event(core_event)
    assert len(adapted_events) == 1
    assert "CustomVendor" in adapted_events[0]["Oem"]
```

#### Integration Testing
```bash
# Test persona endpoints
hawkfish persona set test-vm custom_hardware

# Test custom manager endpoint
curl "$HAWKFISH_URL/redfish/v1/Managers/CustomBMC.1" \
  -H "X-Auth-Token: $TOKEN"
```

## Monitoring and Debugging

### Persona Metrics

Monitor persona usage and performance:

```bash
# Persona usage statistics
curl "$HAWKFISH_URL/redfish/v1/metrics" | grep persona

# Common metrics
hawkfish_persona_requests_total{persona="hpe_ilo5"} 1247
hawkfish_persona_errors_total{persona="hpe_ilo5"} 5
hawkfish_persona_adaptation_duration_seconds{persona="hpe_ilo5"} 0.002
```

### Debug Logging

Enable detailed persona logging:

```bash
# Environment variable
export HF_LOG_LEVEL=DEBUG
export HF_PERSONA_DEBUG=true

# Configuration
hawkfish config set log-level DEBUG
hawkfish config set persona-debug true
```

### Persona Information

Get detailed persona information:

```bash
# List all available personas
hawkfish persona list

# Show persona details
hawkfish persona info hpe_ilo5

# Check system persona assignments
hawkfish systems --show-persona
```

## Best Practices

### Persona Selection

#### Choose the Right Persona
- **HPE iLO**: For environments with existing HPE tooling
- **Dell iDRAC**: For Dell-centric infrastructure
- **Generic**: For maximum Redfish compliance

#### Consistency
- Use consistent personas within projects
- Document persona choices in deployment guides
- Consider migration paths when changing personas

### Performance Considerations

#### Persona Overhead
- Event adaptation adds minimal latency (~1-2ms)
- Endpoint mapping is cached for performance
- Consider generic persona for high-throughput scenarios

#### Resource Usage
- Personas use minimal additional memory
- No significant CPU overhead
- Network traffic patterns may vary by persona

### Security Considerations

#### Compatibility vs Security
- Vendor emulation may expose additional endpoints
- Review persona capabilities before deployment
- Monitor for unexpected API usage patterns

#### Audit Logging
- Persona operations are fully audited
- Event adaptations are logged in debug mode
- Error translations maintain security context

## Troubleshooting

### Common Issues

#### Persona Not Found
```bash
# Check available personas
hawkfish persona list

# Verify persona is registered
grep -i "persona.*registered" /var/log/hawkfish/controller.log
```

#### Endpoint Not Working
```bash
# Check persona endpoint mapping
hawkfish persona info <persona-name>

# Test with generic persona
hawkfish persona set test-vm generic
```

#### Event Adaptation Errors
```bash
# Enable debug logging
export HF_PERSONA_DEBUG=true

# Check adaptation logs
tail -f /var/log/hawkfish/controller.log | grep adaptation
```

### Support Resources

- **HPE Integration**: See [HPE iLO Guide](persona-ilo.md)
- **Dell Integration**: See [Dell iDRAC Guide](persona-idrac.md)
- **Custom Development**: Contact HawkFish development team
- **Conformance Testing**: Use [Conformance Suite](conformance.md)
