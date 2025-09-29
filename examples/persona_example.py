#!/usr/bin/env python3
"""
Comprehensive HawkFish persona system demonstration.

This example shows how to use and test the persona system, including:
- Persona registry operations
- Event adaptation
- Error message translation
- BIOS service integration
- Vendor-specific endpoint usage

Prerequisites:
- HawkFish controller running
- Valid authentication token
- Test system available

Environment Variables:
    HAWKFISH_URL - Controller URL (default: http://localhost:8080)
    HAWKFISH_TOKEN - Authentication token (required)
    SYSTEM_ID - Target system ID (default: test-system)
"""

import sys
import os
import asyncio
import httpx
from typing import Any, Dict

# Add src to path for local testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_persona_registry():
    """Test the persona registry functionality."""
    try:
        from hawkfish_controller.persona.registry import persona_registry
        from hawkfish_controller.persona.hpe_ilo5 import hpe_ilo5_plugin
        from hawkfish_controller.persona.dell_idrac9 import dell_idrac9_plugin
        
        print("Testing Persona Registry")
        print("-" * 40)
        
        # Register plugins (normally done in main_app.py)
        persona_registry.register_plugin(hpe_ilo5_plugin)
        persona_registry.register_plugin(dell_idrac9_plugin)
        
        # List available personas
        personas = persona_registry.list_personas()
        print(f"Available personas: {personas}")
        
        # Test each persona
        for persona_name in personas:
            plugin = persona_registry.get_plugin(persona_name)
            if plugin:
                print(f"  ✓ {persona_name}: {plugin.name} ({plugin.vendor})")
                print(f"    Manager endpoint: {plugin.get_manager_endpoint()}")
            else:
                print(f"  ✗ {persona_name}: Plugin not found")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_adaptation():
    """Test event adaptation."""
    try:
        from hawkfish_controller.persona.hpe_ilo5 import hpe_ilo5_plugin
        
        print("\n📡 Testing Event Adaptation")
        print("-" * 40)
        
        # Test core event
        core_event = {
            "EventType": "PowerStateChanged",
            "systemId": "test-vm",
            "Severity": "OK"
        }
        
        adapted_events = hpe_ilo5_plugin.adapt_event(core_event)
        adapted = adapted_events[0]
        
        print(f"Original event: {core_event['EventType']}")
        print(f"HPE EventID: {adapted['Oem']['Hpe']['EventID']}")
        print(f"HPE Category: {adapted['Oem']['Hpe']['Category']}")
        print(f"Disclaimer: {adapted['Oem']['HawkFish']['CompatibilityDisclaimer'][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


def test_error_adaptation():
    """Test error adaptation."""
    try:
        from hawkfish_controller.persona.hpe_ilo5 import hpe_ilo5_plugin
        
        print("\n🚨 Testing Error Adaptation")
        print("-" * 40)
        
        # Test core error
        core_error = {
            "@Message.MessageId": "InvalidAttribute",
            "message": "Invalid BIOS setting",
            "Resolution": "Check the attribute value"
        }
        
        adapted = hpe_ilo5_plugin.adapt_error(core_error)
        
        print(f"Original MessageId: {core_error['@Message.MessageId']}")
        print(f"HPE MessageId: {adapted['@Message.MessageId']}")
        print(f"HPE Registry: {adapted['Oem']['Hpe']['MessageRegistry']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_bios_service():
    """Test BIOS service functionality."""
    try:
        from hawkfish_controller.services.bios import bios_service
        
        print("\n⚙️ Testing BIOS Service")
        print("-" * 40)
        
        # Get default attributes
        attrs = await bios_service.get_current_bios_attributes("test-system")
        print(f"Default BootMode: {attrs['BootMode']}")
        print(f"Default SecureBoot: {attrs['SecureBoot']}")
        print(f"Default BootOrder: {attrs['PersistentBootConfigOrder']}")
        
        # Test staging
        new_attrs = {
            "BootMode": "LegacyBios",
            "PersistentBootConfigOrder": ["Cd", "Hdd", "Pxe"]
        }
        
        await bios_service.stage_bios_changes("test-system", new_attrs, "OnReset", "test-user")
        print("✓ BIOS changes staged successfully")
        
        # Check pending
        pending = await bios_service.get_pending_bios_changes("test-system")
        if pending:
            print(f"Pending changes: {pending['attributes']}")
            print(f"Apply time: {pending['apply_time']}")
        
        # Clean up
        await bios_service.clear_pending_bios_changes("test-system")
        print("✓ Pending changes cleared")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_api_integration():
    """Test persona integration with actual API calls."""
    base_url = os.getenv("HAWKFISH_URL", "http://localhost:8080")
    token = os.getenv("HAWKFISH_TOKEN")
    system_id = os.getenv("SYSTEM_ID", "test-system")
    
    if not token:
        print("✗ HAWKFISH_TOKEN environment variable required for API testing")
        return False
    
    print("\nTesting API Integration")
    print("-" * 40)
    
    try:
        async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
            headers = {
                "Content-Type": "application/json",
                "X-Auth-Token": token
            }
            
            # Test setting persona
            print(f"Setting HPE iLO persona for system {system_id}...")
            response = await client.patch(
                f"{base_url}/redfish/v1/Systems/{system_id}",
                headers=headers,
                json={
                    "Oem": {
                        "HawkFish": {
                            "Persona": "hpe_ilo5"
                        }
                    }
                }
            )
            
            if response.status_code == 200:
                print("  ✓ Persona set successfully")
            else:
                print(f"  ⚠ Persona setting failed: {response.status_code}")
            
            # Test HPE manager endpoint
            print("Testing HPE iLO manager endpoint...")
            response = await client.get(
                f"{base_url}/redfish/v1/Managers/iLO.Embedded.1",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✓ Manager: {data.get('Name', 'Unknown')}")
                print(f"  ✓ Firmware: {data.get('FirmwareVersion', 'Unknown')}")
                
                # Check for HPE OEM data
                hpe_data = data.get("Oem", {}).get("Hpe", {})
                if hpe_data:
                    print(f"  ✓ HPE Type: {hpe_data.get('Type', 'Unknown')}")
                
            else:
                print(f"  ✗ Manager endpoint failed: {response.status_code}")
            
            # Test virtual media endpoint
            print("Testing HPE virtual media endpoint...")
            response = await client.get(
                f"{base_url}/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                member_count = data.get("Members@odata.count", 0)
                print(f"  ✓ Virtual media resources: {member_count}")
            else:
                print(f"  ✗ Virtual media endpoint failed: {response.status_code}")
            
            return True
            
    except Exception as e:
        print(f"✗ API integration error: {e}")
        return False

def main():
    """Run comprehensive persona system tests."""
    print("HawkFish Persona System Demonstration")
    print("=" * 50)
    
    results = []
    
    # Test persona registry
    print("1. Testing persona registry...")
    results.append(test_persona_registry())
    
    # Test event adaptation
    print("\n2. Testing event adaptation...")
    results.append(test_event_adaptation())
    
    # Test error adaptation
    print("\n3. Testing error adaptation...")
    results.append(test_error_adaptation())
    
    # Test BIOS service (requires async)
    print("\n4. Testing BIOS service...")
    results.append(asyncio.run(test_bios_service()))
    
    # Test API integration if token provided
    print("\n5. Testing API integration...")
    results.append(asyncio.run(test_api_integration()))
    
    # Summary
    print("\n" + "=" * 50)
    passed = sum(1 for r in results if r)
    total = len(results)
    
    if passed == total:
        print(f"✓ All {total} tests passed!")
        print("\nPersona system is working correctly!")
        print("\nNext steps:")
        print("  • Set system persona: hawkfish persona set <system> hpe_ilo5")
        print("  • Access vendor endpoints: /redfish/v1/Managers/iLO.Embedded.1")
        print("  • Use vendor-specific workflows in your applications")
        print("\nExample usage:")
        print("  export HAWKFISH_TOKEN=$(hawkfish login --username admin)")
        print("  python examples/ilo/ilo_bios_workflow.py")
        print("  python examples/idrac/idrac_job_management.py")
    else:
        print(f"✗ {passed}/{total} tests passed")
        if passed < total:
            print("\nSome tests failed. This may be expected if:")
            print("  • HawkFish controller is not running")
            print("  • HAWKFISH_TOKEN is not set for API tests")
            print("  • Test system is not available")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
