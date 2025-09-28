"""
HPE iLO BIOS/UEFI interoperability test flows.

Tests BIOS configuration via HPE endpoints with ApplyTime staging.
"""

import pytest


class TestIloBiosFlow:
    """Test BIOS operations via HPE iLO endpoints."""
    
    def test_ilo_bios_current_settings(self, client, operator_headers, test_system_id, skip_if_ilo_disabled):
        """Test reading current BIOS settings via HPE endpoint."""
        response = client.get(
            f"/redfish/v1/Systems/{test_system_id}/Bios",
            headers=operator_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate BIOS structure
        assert data["@odata.type"] == "#Bios.v1_1_0.Bios"
        assert data["@odata.id"] == f"/redfish/v1/Systems/{test_system_id}/Bios"
        assert data["Id"] == "BIOS"
        assert data["Name"] == "BIOS Configuration Current Settings"
        assert data["AttributeRegistry"] == "BiosAttributeRegistry.v1_0_0"
        
        # Validate core attributes are present
        attributes = data["Attributes"]
        assert "BootMode" in attributes
        assert "SecureBoot" in attributes  
        assert "PersistentBootConfigOrder" in attributes
        
        # Validate default values
        assert attributes["BootMode"] in ["Uefi", "LegacyBios"]
        assert attributes["SecureBoot"] in ["Enabled", "Disabled"]
        assert isinstance(attributes["PersistentBootConfigOrder"], list)
        
        # Validate Links
        assert "Links" in data
        assert "Settings" in data["Links"]
        settings_link = data["Links"]["Settings"]["@odata.id"]
        assert settings_link == f"/redfish/v1/Systems/{test_system_id}/Bios/Settings"
        
        # Validate HPE OEM data
        assert "Oem" in data
        assert "Hpe" in data["Oem"]
        assert "PendingChanges" in data["Oem"]["Hpe"]
        assert isinstance(data["Oem"]["Hpe"]["PendingChanges"], bool)
        
        # Validate compatibility disclaimer
        assert "HawkFish" in data["Oem"]
        assert "CompatibilityDisclaimer" in data["Oem"]["HawkFish"]
    
    def test_bios_onreset_staging_flow(self, client, operator_headers, test_system_id, skip_if_ilo_disabled):
        """Test BIOS staging with ApplyTime=OnReset → Reset → Apply flow."""
        
        # Step 1: Stage BIOS changes
        bios_changes = {
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
        
        stage_response = client.patch(
            f"/redfish/v1/Systems/{test_system_id}/Bios/Settings",
            headers=operator_headers,
            json=bios_changes
        )
        
        assert stage_response.status_code == 200
        stage_data = stage_response.json()
        assert stage_data["TaskState"] == "Pending"
        assert "OnReset" in stage_data["Message"]
        
        # Validate HPE OEM response
        assert "Oem" in stage_data
        assert "Hpe" in stage_data["Oem"]
        assert stage_data["Oem"]["Hpe"]["ApplyTime"] == "OnReset"
        assert "HawkFish" in stage_data["Oem"]
        
        # Step 2: Verify changes are pending
        check_response = client.get(
            f"/redfish/v1/Systems/{test_system_id}/Bios",
            headers=operator_headers
        )
        
        assert check_response.status_code == 200
        check_data = check_response.json()
        assert check_data["Oem"]["Hpe"]["PendingChanges"] is True
        
        # Step 3: Apply changes via system reset
        reset_response = client.post(
            f"/redfish/v1/Systems/{test_system_id}/Actions/ComputerSystem.Reset",
            headers=operator_headers,
            json={"ResetType": "ForceRestart"}
        )
        
        assert reset_response.status_code == 200
        reset_data = reset_response.json()
        assert reset_data["TaskState"] == "Completed"
        
        # Step 4: Verify changes are no longer pending
        final_response = client.get(
            f"/redfish/v1/Systems/{test_system_id}/Bios",
            headers=operator_headers
        )
        
        assert final_response.status_code == 200
        final_data = final_response.json()
        assert final_data["Oem"]["Hpe"]["PendingChanges"] is False
    
    def test_bios_immediate_validation(self, client, operator_headers, test_system_id, skip_if_ilo_disabled):
        """Test BIOS immediate application validation."""
        
        # Test immediate application that should require power-off
        bios_changes = {
            "Attributes": {
                "BootMode": "LegacyBios"  # This typically requires reboot
            },
            "Oem": {
                "Hpe": {
                    "ApplyTime": "Immediate"
                }
            }
        }
        
        response = client.patch(
            f"/redfish/v1/Systems/{test_system_id}/Bios/Settings",
            headers=operator_headers,
            json=bios_changes
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        # Validate HPE error structure
        assert "error" in error_data["detail"]
        error = error_data["detail"]["error"]
        assert error["code"] == "Oem.Hpe.Bios.RequiresPowerOff"
        
        # Validate ExtendedInfo
        assert "@Message.ExtendedInfo" in error
        extended_info = error["@Message.ExtendedInfo"][0]
        assert extended_info["MessageId"] == "Oem.Hpe.Bios.RequiresPowerOff"
        assert "ApplyTime=OnReset" in extended_info["Message"]
        assert "Resolution" in extended_info
        assert extended_info["Severity"] == "Warning"
    
    def test_bios_secureboot_validation(self, client, operator_headers, test_system_id, skip_if_ilo_disabled):
        """Test SecureBoot requires UEFI validation."""
        
        # Try to enable SecureBoot with LegacyBios
        bios_changes = {
            "Attributes": {
                "BootMode": "LegacyBios",
                "SecureBoot": "Enabled"
            },
            "Oem": {
                "Hpe": {
                    "ApplyTime": "OnReset"
                }
            }
        }
        
        response = client.patch(
            f"/redfish/v1/Systems/{test_system_id}/Bios/Settings",
            headers=operator_headers,
            json=bios_changes
        )
        
        assert response.status_code == 400
        error_data = response.json()
        
        # Validate HPE error structure
        assert "error" in error_data["detail"]
        error = error_data["detail"]["error"]
        assert error["code"] == "Oem.Hpe.Bios.InvalidAttribute"
        
        # Validate ExtendedInfo
        assert "@Message.ExtendedInfo" in error
        extended_info = error["@Message.ExtendedInfo"][0]
        assert extended_info["MessageId"] == "Oem.Hpe.Bios.InvalidAttribute"
        assert "SecureBoot requires UEFI" in extended_info["Message"]
    
    def test_bios_attribute_validation(self, client, operator_headers, test_system_id, skip_if_ilo_disabled):
        """Test BIOS attribute validation."""
        
        # Test invalid BootMode
        bios_changes = {
            "Attributes": {
                "BootMode": "InvalidMode"
            },
            "Oem": {
                "Hpe": {
                    "ApplyTime": "OnReset"
                }
            }
        }
        
        response = client.patch(
            f"/redfish/v1/Systems/{test_system_id}/Bios/Settings",
            headers=operator_headers,
            json=bios_changes
        )
        
        assert response.status_code == 400
        error_data = response.json()
        assert "error" in error_data["detail"]
        
        # Test invalid boot order device
        bios_changes = {
            "Attributes": {
                "PersistentBootConfigOrder": ["Cd", "InvalidDevice", "Hdd"]
            },
            "Oem": {
                "Hpe": {
                    "ApplyTime": "OnReset"
                }
            }
        }
        
        response = client.patch(
            f"/redfish/v1/Systems/{test_system_id}/Bios/Settings",
            headers=operator_headers,
            json=bios_changes
        )
        
        assert response.status_code == 400
    
    def test_bios_rbac_enforcement(self, client, test_system_id, skip_if_ilo_disabled):
        """Test RBAC enforcement on BIOS operations."""
        
        # Test without authentication
        response = client.patch(
            f"/redfish/v1/Systems/{test_system_id}/Bios/Settings",
            json={"Attributes": {"BootMode": "Uefi"}}
        )
        
        assert response.status_code == 401  # Unauthorized
        
        # Test with viewer role (should fail)
        from hawkfish_controller.api.sessions import global_session_store
        from hawkfish_controller.services.sessions import Session
        
        global_session_store.sessions["viewer-token"] = Session("viewer", "viewer", "viewer-token")
        viewer_headers = {"X-Auth-Token": "viewer-token"}
        
        response = client.patch(
            f"/redfish/v1/Systems/{test_system_id}/Bios/Settings",
            headers=viewer_headers,
            json={"Attributes": {"BootMode": "Uefi"}}
        )
        
        assert response.status_code == 403  # Forbidden
