#!/usr/bin/env python3
"""
Example script demonstrating HPE iLO persona functionality.
"""

import sys
import os

# Add src to path for local testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_persona_registry():
    """Test the persona registry."""
    try:
        from hawkfish_controller.persona.registry import persona_registry
        from hawkfish_controller.persona.hpe_ilo5 import hpe_ilo5_plugin
        
        print("🔌 Testing Persona Registry")
        print("-" * 40)
        
        # Register the plugin (normally done in main_app.py)
        persona_registry.register_plugin(hpe_ilo5_plugin)
        
        # List available personas
        personas = persona_registry.list_personas()
        print(f"Available personas: {personas}")
        
        # Get HPE plugin
        hpe_plugin = persona_registry.get_plugin("hpe_ilo5")
        if hpe_plugin:
            print(f"✓ HPE iLO5 plugin loaded: {hpe_plugin.name}")
        else:
            print("✗ HPE iLO5 plugin not found")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
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


def main():
    """Run all tests."""
    print("🚀 HawkFish M12 Persona System Test")
    print("=" * 50)
    
    results = []
    
    # Test persona registry
    results.append(test_persona_registry())
    
    # Test event adaptation
    results.append(test_event_adaptation())
    
    # Test error adaptation
    results.append(test_error_adaptation())
    
    # Test BIOS service (requires async)
    import asyncio
    results.append(asyncio.run(test_bios_service()))
    
    print("\n" + "=" * 50)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"🎉 All {total} tests passed!")
        print("\n✨ HPE iLO5 persona system is working correctly!")
        print("\nNext steps:")
        print("  • Configure system persona: hawkfish persona set <system> hpe_ilo5")
        print("  • Access HPE endpoints: /redfish/v1/Managers/iLO.Embedded.1")
        print("  • Manage BIOS settings: hawkfish bios set <system> --boot-mode uefi")
    else:
        print(f"❌ {passed}/{total} tests passed")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
