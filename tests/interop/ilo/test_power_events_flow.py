"""
HPE iLO Power operations and event adaptation tests.

Tests power operations and validates HPE-specific event formatting.
"""

import pytest


class TestIloPowerEventsFlow:
    """Test power operations with HPE event adaptation."""
    
    def test_ilo_manager_resource(self, client, operator_headers, skip_if_ilo_disabled):
        """Test HPE iLO Manager resource structure."""
        response = client.get(
            "/redfish/v1/Managers/iLO.Embedded.1",
            headers=operator_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate HPE Manager structure
        assert data["@odata.type"] == "#Manager.v1_10_0.Manager"
        assert data["@odata.id"] == "/redfish/v1/Managers/iLO.Embedded.1"
        assert data["Id"] == "iLO.Embedded.1"
        assert data["ManagerType"] == "BMC"
        
        # Validate HPE-compatible manufacturer
        assert "HawkFish (HPE iLO-compatible mode)" in data["Manufacturer"]
        assert data["Model"] == "Integrated Lights-Out 5"
        assert "HawkFish-" in data["FirmwareVersion"]
        assert "-ilo5" in data["FirmwareVersion"]
        
        # Validate status and links
        assert data["Status"]["State"] == "Enabled"
        assert data["Status"]["Health"] == "OK"
        assert "/VirtualMedia" in data["Links"]["VirtualMedia"]["@odata.id"]
        
        # Validate compatibility disclaimer
        oem_hawkfish = data["Oem"]["HawkFish"]
        assert "CompatibilityDisclaimer" in oem_hawkfish
        assert "not affiliated with HPE" in oem_hawkfish["CompatibilityDisclaimer"]
    
    def test_power_operation_via_standard_endpoint(self, client, operator_headers, test_system_id, skip_if_ilo_disabled):
        """Test power operations via standard Redfish (events should be HPE-adapted)."""
        # Test power on
        response = client.post(
            f"/redfish/v1/Systems/{test_system_id}/Actions/ComputerSystem.Reset",
            headers=operator_headers,
            json={"ResetType": "On"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["TaskState"] == "Completed"
        
        # Test force restart
        response = client.post(
            f"/redfish/v1/Systems/{test_system_id}/Actions/ComputerSystem.Reset",
            headers=operator_headers,
            json={"ResetType": "ForceRestart"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["TaskState"] == "Completed"
        
        # Test graceful shutdown
        response = client.post(
            f"/redfish/v1/Systems/{test_system_id}/Actions/ComputerSystem.Reset",
            headers=operator_headers,
            json={"ResetType": "GracefulShutdown"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["TaskState"] == "Completed"
    
    def test_system_information_structure(self, client, operator_headers, test_system_id, skip_if_ilo_disabled):
        """Test that system information includes proper HPE formatting when persona is active."""
        response = client.get(
            f"/redfish/v1/Systems/{test_system_id}",
            headers=operator_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Standard Redfish structure should still be present
        assert data["@odata.type"] == "#ComputerSystem.v1_17_0.ComputerSystem"
        assert data["Id"] == test_system_id
        assert data["Name"]
        assert "PowerState" in data
        assert "ProcessorSummary" in data
        assert "MemorySummary" in data
        
        # Links should be present
        assert "Links" in data
        assert "Chassis" in data["Links"]
        assert "ManagedBy" in data["Links"]
    
    def test_event_adaptation_verification(self, client, operator_headers, test_system_id, skip_if_ilo_disabled):
        """Verify that events get HPE adaptation when persona is active."""
        # This is a structural test - actual event verification would require
        # event subscription and WebSocket testing
        
        # Get the persona registry to verify adaptation capability
        from hawkfish_controller.persona.registry import persona_registry
        
        hpe_plugin = persona_registry.get_plugin("hpe_ilo5")
        assert hpe_plugin is not None
        
        # Test event adaptation
        core_event = {
            "EventType": "PowerStateChanged",
            "systemId": test_system_id,
            "details": {"reset": "On"}
        }
        
        adapted_events = hpe_plugin.adapt_event(core_event)
        assert len(adapted_events) == 1
        
        adapted = adapted_events[0]
        assert "Oem" in adapted
        assert "Hpe" in adapted["Oem"]
        
        hpe_oem = adapted["Oem"]["Hpe"]
        assert "EventID" in hpe_oem
        assert "Category" in hpe_oem
        assert hpe_oem["Category"] == "Power"  # PowerStateChanged → Power category
        assert "Severity" in hpe_oem
        
        # Verify disclaimer is included
        assert "HawkFish" in adapted["Oem"]
        assert "CompatibilityDisclaimer" in adapted["Oem"]["HawkFish"]
    
    def test_power_operation_rbac(self, client, test_system_id, skip_if_ilo_disabled):
        """Test RBAC enforcement on power operations."""
        # Test without authentication
        response = client.post(
            f"/redfish/v1/Systems/{test_system_id}/Actions/ComputerSystem.Reset",
            json={"ResetType": "On"}
        )
        
        assert response.status_code == 401  # Unauthorized
        
        # Test with viewer role (should fail)
        from hawkfish_controller.api.sessions import global_session_store
        from hawkfish_controller.services.sessions import Session
        
        global_session_store.sessions["viewer-token"] = Session("viewer", "viewer", "viewer-token")
        viewer_headers = {"X-Auth-Token": "viewer-token"}
        
        response = client.post(
            f"/redfish/v1/Systems/{test_system_id}/Actions/ComputerSystem.Reset",
            headers=viewer_headers,
            json={"ResetType": "On"}
        )
        
        assert response.status_code == 403  # Forbidden
