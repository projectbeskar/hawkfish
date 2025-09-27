"""
Dell iDRAC VirtualMedia interoperability test flows.

Tests exercise only Dell iDRAC endpoints to validate vendor compatibility.
"""

import pytest


class TestIdracVirtualMediaFlow:
    """Test VirtualMedia operations via Dell iDRAC endpoints only."""
    
    def test_idrac_manager_identity(self, client, operator_headers, skip_if_idrac_disabled):
        """Test Dell iDRAC Manager resource structure."""
        response = client.get(
            "/redfish/v1/Managers/iDRAC.Embedded.1",
            headers=operator_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate Dell Manager structure
        assert data["@odata.type"] == "#Manager.v1_10_0.Manager"
        assert data["@odata.id"] == "/redfish/v1/Managers/iDRAC.Embedded.1"
        assert data["Id"] == "iDRAC.Embedded.1"
        assert data["ManagerType"] == "BMC"
        
        # Validate Dell-compatible manufacturer
        assert "HawkFish (Dell iDRAC-compatible mode)" in data["Manufacturer"]
        assert data["Model"] == "Integrated Dell Remote Access Controller 9"
        assert "HawkFish-" in data["FirmwareVersion"]
        assert "-idrac9" in data["FirmwareVersion"]
        
        # Validate Dell OEM data
        assert "Dell" in data["Oem"]
        assert "DellManager" in data["Oem"]["Dell"]
        assert data["Oem"]["Dell"]["DellManager"]["DellManagerType"] == "iDRAC"
        
        # Validate compatibility disclaimer
        assert "HawkFish" in data["Oem"]
        assert "CompatibilityDisclaimer" in data["Oem"]["HawkFish"]
        assert "not affiliated with Dell" in data["Oem"]["HawkFish"]["CompatibilityDisclaimer"]
    
    def test_idrac_virtual_media_collection(self, client, operator_headers, skip_if_idrac_disabled):
        """Test Dell iDRAC VirtualMedia collection endpoint."""
        response = client.get(
            "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia",
            headers=operator_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate Dell-specific structure
        assert data["@odata.type"] == "#VirtualMediaCollection.VirtualMediaCollection"
        assert data["Name"] == "Virtual Media Services"
        assert len(data["Members"]) == 1
        assert data["Members"][0]["@odata.id"] == "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD"
        
        # Validate compatibility disclaimer
        assert "HawkFish" in data["Oem"]
        assert "CompatibilityDisclaimer" in data["Oem"]["HawkFish"]
    
    def test_idrac_virtual_media_cd_resource(self, client, operator_headers, skip_if_idrac_disabled):
        """Test Dell iDRAC CD VirtualMedia resource."""
        response = client.get(
            "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD",
            headers=operator_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate Dell CD resource structure
        assert data["@odata.type"] == "#VirtualMedia.v1_3_0.VirtualMedia"
        assert data["Id"] == "CD"
        assert data["Name"] == "Virtual CD"
        assert "CD" in data["MediaTypes"]
        assert "DVD" in data["MediaTypes"]
        assert data["WriteProtected"] is True
        
        # Validate Dell-specific actions
        actions = data["Actions"]["Oem"]
        assert "DellVirtualMedia.v1_0_0#DellVirtualMedia.InsertVirtualMedia" in actions
        assert "DellVirtualMedia.v1_0_0#DellVirtualMedia.EjectVirtualMedia" in actions
        
        insert_target = actions["DellVirtualMedia.v1_0_0#DellVirtualMedia.InsertVirtualMedia"]["target"]
        assert "iDRAC.Embedded.1" in insert_target
        assert "DellVirtualMedia.InsertVirtualMedia" in insert_target
    
    def test_idrac_insert_eject_media_flow(self, client, operator_headers, test_system_id, skip_if_idrac_disabled):
        """Test complete Insert → Eject flow via Dell iDRAC endpoints."""
        iso_url = "http://example.com/ubuntu-22.04.iso"
        
        # Step 1: Insert media via Dell endpoint
        insert_response = client.post(
            "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/Oem/DellVirtualMedia.InsertVirtualMedia",
            headers=operator_headers,
            json={
                "SystemId": test_system_id,
                "Image": iso_url
            }
        )
        
        assert insert_response.status_code == 200
        insert_data = insert_response.json()
        assert insert_data["TaskState"] == "Completed"
        
        # Validate Dell OEM response
        assert "Dell" in insert_data["Oem"]
        assert insert_data["Oem"]["Dell"]["JobStatus"] == "Completed"
        
        # Step 2: Eject media via Dell endpoint
        eject_response = client.post(
            "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/Oem/DellVirtualMedia.EjectVirtualMedia",
            headers=operator_headers,
            json={"SystemId": test_system_id}
        )
        
        assert eject_response.status_code == 200
        eject_data = eject_response.json()
        assert eject_data["TaskState"] == "Completed"
        
        # Validate Dell OEM response
        assert "Dell" in eject_data["Oem"]
        assert eject_data["Oem"]["Dell"]["JobStatus"] == "Completed"
    
    def test_idrac_insert_media_validation(self, client, operator_headers, skip_if_idrac_disabled):
        """Test Dell iDRAC media insertion validation."""
        # Test missing SystemId
        response = client.post(
            "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/Oem/DellVirtualMedia.InsertVirtualMedia",
            headers=operator_headers,
            json={"Image": "http://example.com/test.iso"}
        )
        
        assert response.status_code == 400
        assert "SystemId" in response.json()["detail"] or "Target" in response.json()["detail"]
        
        # Test missing Image
        response = client.post(
            "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/Oem/DellVirtualMedia.InsertVirtualMedia",
            headers=operator_headers,
            json={"SystemId": "test-vm"}
        )
        
        assert response.status_code == 400
        assert "Image" in response.json()["detail"]
    
    def test_idrac_media_rbac(self, client, skip_if_idrac_disabled):
        """Test RBAC enforcement on Dell iDRAC media operations."""
        # Test without authentication
        response = client.post(
            "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/Oem/DellVirtualMedia.InsertVirtualMedia",
            json={"SystemId": "test-vm", "Image": "http://example.com/test.iso"}
        )
        
        assert response.status_code == 401  # Unauthorized
        
        # Test with viewer role (should fail)
        viewer_session = {"X-Auth-Token": "viewer-token"}
        from src.hawkfish_controller.api.sessions import global_session_store
        from src.hawkfish_controller.services.sessions import Session
        
        global_session_store.sessions["viewer-token"] = Session("viewer", "viewer", "viewer-token")
        
        response = client.post(
            "/redfish/v1/Managers/iDRAC.Embedded.1/VirtualMedia/CD/Actions/Oem/DellVirtualMedia.InsertVirtualMedia",
            headers=viewer_session,
            json={"SystemId": "test-vm", "Image": "http://example.com/test.iso"}
        )
        
        assert response.status_code == 403  # Forbidden
