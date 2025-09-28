"""
HPE iLO VirtualMedia interoperability test flows.

Tests exercise only HPE iLO endpoints to validate vendor compatibility.
"""

import pytest


class TestIloVirtualMediaFlow:
    """Test VirtualMedia operations via HPE iLO endpoints only."""
    
    def test_ilo_virtual_media_collection(self, client, operator_headers, skip_if_ilo_disabled):
        """Test HPE iLO VirtualMedia collection endpoint."""
        response = client.get(
            "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia",
            headers=operator_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate HPE-specific structure
        assert data["@odata.type"] == "#VirtualMediaCollection.VirtualMediaCollection"
        assert data["Name"] == "Virtual Media Services"
        assert len(data["Members"]) == 1
        assert data["Members"][0]["@odata.id"] == "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1"
        
        # Validate compatibility disclaimer
        assert "HawkFish" in data["Oem"]
        assert "CompatibilityDisclaimer" in data["Oem"]["HawkFish"]
        assert "not affiliated with HPE" in data["Oem"]["HawkFish"]["CompatibilityDisclaimer"]
    
    def test_ilo_virtual_media_cd_resource(self, client, operator_headers, skip_if_ilo_disabled):
        """Test HPE iLO CD VirtualMedia resource."""
        response = client.get(
            "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1",
            headers=operator_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validate HPE CD resource structure
        assert data["@odata.type"] == "#VirtualMedia.v1_3_0.VirtualMedia"
        assert data["Id"] == "CD1"
        assert data["Name"] == "Virtual Removable Media"
        assert "CD" in data["MediaTypes"]
        assert "DVD" in data["MediaTypes"]
        assert data["WriteProtected"] is True
        
        # Validate actions are present
        actions = data["Actions"]
        assert "#VirtualMedia.InsertMedia" in actions
        assert "#VirtualMedia.EjectMedia" in actions
        
        insert_target = actions["#VirtualMedia.InsertMedia"]["target"]
        assert "iLO.Embedded.1" in insert_target
        assert "VirtualMedia.InsertMedia" in insert_target
    
    def test_ilo_insert_eject_media_flow(self, client, operator_headers, test_system_id, skip_if_ilo_disabled):
        """Test complete Insert → Eject flow via HPE iLO endpoints."""
        iso_url = "http://example.com/ubuntu-22.04.iso"
        
        # Step 1: Insert media via HPE endpoint
        insert_response = client.post(
            "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1/Actions/VirtualMedia.InsertMedia",
            headers=operator_headers,
            json={
                "SystemId": test_system_id,
                "Image": iso_url
            }
        )
        
        assert insert_response.status_code == 200
        insert_data = insert_response.json()
        assert insert_data["TaskState"] == "Completed"
        
        # Step 2: Verify media is attached (check via standard endpoint for verification)
        verify_response = client.get(
            f"/redfish/v1/Systems/{test_system_id}",
            headers=operator_headers
        )
        assert verify_response.status_code == 200
        
        # Step 3: Eject media via HPE endpoint
        eject_response = client.post(
            "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1/Actions/VirtualMedia.EjectMedia",
            headers=operator_headers,
            json={"SystemId": test_system_id}
        )
        
        assert eject_response.status_code == 200
        eject_data = eject_response.json()
        assert eject_data["TaskState"] == "Completed"
    
    def test_ilo_insert_media_validation(self, client, operator_headers, skip_if_ilo_disabled):
        """Test HPE iLO media insertion validation."""
        # Test missing SystemId
        response = client.post(
            "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1/Actions/VirtualMedia.InsertMedia",
            headers=operator_headers,
            json={"Image": "http://example.com/test.iso"}
        )
        
        assert response.status_code == 400
        assert "SystemId" in response.json()["detail"]
        
        # Test missing Image
        response = client.post(
            "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1/Actions/VirtualMedia.InsertMedia",
            headers=operator_headers,
            json={"SystemId": "test-vm"}
        )
        
        assert response.status_code == 400
        assert "Image" in response.json()["detail"]
    
    def test_ilo_media_rbac(self, client, skip_if_ilo_disabled):
        """Test RBAC enforcement on HPE iLO media operations."""
        # Test without authentication
        response = client.post(
            "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1/Actions/VirtualMedia.InsertMedia",
            json={"SystemId": "test-vm", "Image": "http://example.com/test.iso"}
        )
        
        assert response.status_code == 401  # Unauthorized
        
        # Test with viewer role (should fail)
        viewer_session = {"X-Auth-Token": "viewer-token"}
        from hawkfish_controller.api.sessions import global_session_store
        from hawkfish_controller.services.sessions import Session
        
        global_session_store.sessions["viewer-token"] = Session("viewer", "viewer", "viewer-token")
        
        response = client.post(
            "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1/Actions/VirtualMedia.InsertMedia",
            headers=viewer_session,
            json={"SystemId": "test-vm", "Image": "http://example.com/test.iso"}
        )
        
        assert response.status_code == 403  # Forbidden
