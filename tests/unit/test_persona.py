"""
Tests for persona system functionality.
"""

import pytest
import tempfile
import os
import asyncio
from pathlib import Path
from fastapi.testclient import TestClient

from hawkfish_controller.main_app import create_app
from hawkfish_controller.persona.registry import persona_registry
from hawkfish_controller.services.persona import persona_service


class TestPersonaRegistry:
    """Tests for persona registry functionality."""
    
    def test_list_personas(self):
        """Test listing available personas."""
        # Register personas for testing
        from hawkfish_controller.persona.hpe_ilo5 import hpe_ilo5_plugin
        from hawkfish_controller.persona.dell_idrac9 import dell_idrac9_plugin
        persona_registry.register_plugin(hpe_ilo5_plugin)
        persona_registry.register_plugin(dell_idrac9_plugin)
        
        personas = persona_registry.list_personas()
        assert "hpe_ilo5" in personas
    
    def test_get_hpe_plugin(self):
        """Test getting HPE iLO5 plugin."""
        # Register personas for testing
        from hawkfish_controller.persona.hpe_ilo5 import hpe_ilo5_plugin
        persona_registry.register_plugin(hpe_ilo5_plugin)
        
        plugin = persona_registry.get_plugin("hpe_ilo5")
        assert plugin is not None
        assert plugin.name == "hpe_ilo5"
    
    def test_get_nonexistent_plugin(self):
        """Test getting nonexistent plugin returns None."""
        plugin = persona_registry.get_plugin("nonexistent")
        assert plugin is None


class TestPersonaAPI:
    """Tests for persona API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Mock auth headers."""
        return {"X-Auth-Token": "test-token"}
    
    def test_list_personas_endpoint(self, client, auth_headers):
        """Test persona list endpoint."""
        # Mock session
        from hawkfish_controller.api.sessions import global_session_store
        from hawkfish_controller.services.sessions import Session
        
        import time
        now = time.time()
        session = Session(
            token="test-token",
            username="test-user",
            role="admin",
            created_at=now,
            expires_at=now + 3600,  # 1 hour
            last_activity=now
        )
        global_session_store._token_to_session["test-token"] = session
        
        response = client.get("/redfish/v1/Oem/HawkFish/Personas", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert "@odata.type" in data
        assert "Members" in data
        
        # Check that generic and hpe_ilo5 are available
        member_names = [member["Name"] for member in data["Members"]]
        assert "generic" in member_names
        assert "hpe_ilo5" in member_names
    
    def test_get_persona_info(self, client, auth_headers):
        """Test getting persona info."""
        from hawkfish_controller.api.sessions import global_session_store
        from hawkfish_controller.services.sessions import Session
        
        import time
        now = time.time()
        session = Session(
            token="test-token",
            username="test-user",
            role="admin",
            created_at=now,
            expires_at=now + 3600,  # 1 hour
            last_activity=now
        )
        global_session_store._token_to_session["test-token"] = session
        
        # Test generic persona
        response = client.get("/redfish/v1/Oem/HawkFish/Personas/generic", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["Id"] == "generic"
        assert data["Name"] == "Generic Redfish"
        
        # Test HPE persona
        response = client.get("/redfish/v1/Oem/HawkFish/Personas/hpe_ilo5", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["Id"] == "hpe_ilo5"


class TestHpeIlo5Plugin:
    """Tests for HPE iLO5 plugin functionality."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        return TestClient(app)
    
    @pytest.fixture
    def auth_headers(self):
        """Mock auth headers."""
        return {"X-Auth-Token": "test-token"}
    
    def test_hpe_manager_endpoint(self, client, auth_headers):
        """Test HPE iLO Manager endpoint."""
        from hawkfish_controller.api.sessions import global_session_store
        from hawkfish_controller.services.sessions import Session
        
        import time
        now = time.time()
        session = Session(
            token="test-token",
            username="test-user",
            role="admin",
            created_at=now,
            expires_at=now + 3600,  # 1 hour
            last_activity=now
        )
        global_session_store._token_to_session["test-token"] = session
        
        response = client.get("/redfish/v1/Managers/iLO.Embedded.1", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["Id"] == "iLO.Embedded.1"
        assert data["ManagerType"] == "BMC"
        assert "HawkFish (HPE iLO-compatible mode)" in data["Manufacturer"]
        
        # Check for disclaimer
        assert "CompatibilityDisclaimer" in data["Oem"]["HawkFish"]
        assert "not affiliated with HPE" in data["Oem"]["HawkFish"]["CompatibilityDisclaimer"]
    
    def test_hpe_virtual_media_collection(self, client, auth_headers):
        """Test HPE VirtualMedia collection endpoint."""
        from hawkfish_controller.api.sessions import global_session_store
        from hawkfish_controller.services.sessions import Session
        
        import time
        now = time.time()
        session = Session(
            token="test-token",
            username="test-user",
            role="admin",
            created_at=now,
            expires_at=now + 3600,  # 1 hour
            last_activity=now
        )
        global_session_store._token_to_session["test-token"] = session
        
        response = client.get("/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["@odata.type"] == "#VirtualMediaCollection.VirtualMediaCollection"
        assert len(data["Members"]) == 1
        assert data["Members"][0]["@odata.id"] == "/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1"
    
    def test_hpe_virtual_media_cd(self, client, auth_headers):
        """Test HPE VirtualMedia CD endpoint."""
        from hawkfish_controller.api.sessions import global_session_store
        from hawkfish_controller.services.sessions import Session
        
        import time
        now = time.time()
        session = Session(
            token="test-token",
            username="test-user",
            role="admin",
            created_at=now,
            expires_at=now + 3600,  # 1 hour
            last_activity=now
        )
        global_session_store._token_to_session["test-token"] = session
        
        response = client.get("/redfish/v1/Managers/iLO.Embedded.1/VirtualMedia/CD1", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["Id"] == "CD1"
        assert "CD" in data["MediaTypes"]
        assert "DVD" in data["MediaTypes"]
        
        # Check actions
        assert "#VirtualMedia.InsertMedia" in data["Actions"]
        assert "#VirtualMedia.EjectMedia" in data["Actions"]
    
    def test_event_adaptation(self):
        """Test event adaptation by HPE plugin."""
        from hawkfish_controller.persona.hpe_ilo5 import hpe_ilo5_plugin
        
        core_event = {
            "EventType": "PowerStateChanged",
            "systemId": "test-system"
        }
        
        adapted_events = hpe_ilo5_plugin.adapt_event(core_event)
        assert len(adapted_events) == 1
        
        adapted = adapted_events[0]
        assert "Oem" in adapted
        assert "Hpe" in adapted["Oem"]
        assert "HawkFish" in adapted["Oem"]
        
        hpe_oem = adapted["Oem"]["Hpe"]
        assert "EventID" in hpe_oem
        assert "Category" in hpe_oem
        assert hpe_oem["Category"] == "Power"
        
        # Check disclaimer
        hawkfish_oem = adapted["Oem"]["HawkFish"]
        assert "CompatibilityDisclaimer" in hawkfish_oem
    
    def test_error_adaptation(self):
        """Test error adaptation by HPE plugin."""
        from hawkfish_controller.persona.hpe_ilo5 import hpe_ilo5_plugin
        
        core_error = {
            "@Message.MessageId": "InvalidAttribute",
            "message": "Invalid BIOS attribute"
        }
        
        adapted = hpe_ilo5_plugin.adapt_error(core_error)
        assert adapted["@Message.MessageId"] == "Oem.Hpe.Bios.InvalidAttribute"
        assert "Oem" in adapted
        assert "Hpe" in adapted["Oem"]
        
        hpe_oem = adapted["Oem"]["Hpe"]
        assert "MessageRegistry" in hpe_oem
        assert "Resolution" in hpe_oem


class TestBiosService:
    """Tests for BIOS service functionality."""
    
    async def _setup_test_db(self):
        """Set up test database for BIOS service."""
        from hawkfish_controller.config import settings
        from hawkfish_controller.services.projects import project_store
        
        # Create a temporary directory for testing
        self._tmp_dir = tempfile.mkdtemp()
        
        # Set the state directory to temp directory  
        settings.state_dir = self._tmp_dir
        
        # Ensure the directory exists
        os.makedirs(self._tmp_dir, exist_ok=True)
        
        # Update project store to use the temp directory
        project_store.db_path = os.path.join(self._tmp_dir, "hawkfish.db")
        
        # Initialize database tables
        await project_store.init()
        
        # Also update the bios service to use the same database
        from hawkfish_controller.services.bios import bios_service
        bios_service.db_path = os.path.join(self._tmp_dir, "hawkfish.db")
        
        # Initialize BIOS tables specifically (they should be created by project_store.init() but let's be sure)
        import aiosqlite
        async with aiosqlite.connect(bios_service.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS hf_bios_pending (
                    system_id TEXT NOT NULL,
                    attributes TEXT NOT NULL,
                    apply_time TEXT NOT NULL DEFAULT 'OnReset',
                    staged_at TEXT NOT NULL,
                    staged_by TEXT NOT NULL,
                    PRIMARY KEY (system_id)
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS hf_bios_applied (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    system_id TEXT NOT NULL,
                    attributes TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    applied_by TEXT NOT NULL
                )
            """)
            await db.commit()
    
    @pytest.mark.asyncio
    async def test_get_default_bios_attributes(self):
        """Test getting default BIOS attributes."""
        await self._setup_test_db()
        
        from hawkfish_controller.services.bios import bios_service
        
        attrs = await bios_service.get_current_bios_attributes("test-system")
        assert "BootMode" in attrs
        assert "SecureBoot" in attrs
        assert "PersistentBootConfigOrder" in attrs
        
        assert attrs["BootMode"] == "Uefi"
        assert attrs["SecureBoot"] == "Disabled"
        assert isinstance(attrs["PersistentBootConfigOrder"], list)
    
    @pytest.mark.asyncio
    async def test_stage_bios_changes(self):
        """Test staging BIOS changes."""
        await self._setup_test_db()
        
        from hawkfish_controller.services.bios import bios_service
        
        attributes = {
            "BootMode": "LegacyBios",
            "PersistentBootConfigOrder": ["Cd", "Hdd", "Pxe"]
        }
        
        await bios_service.stage_bios_changes(
            "test-system", attributes, "OnReset", "test-user"
        )
        
        pending = await bios_service.get_pending_bios_changes("test-system")
        assert pending is not None
        assert pending["attributes"]["BootMode"] == "LegacyBios"
        assert pending["apply_time"] == "OnReset"
        assert pending["staged_by"] == "test-user"
    
    @pytest.mark.asyncio
    async def test_bios_validation_secure_boot_requires_uefi(self):
        """Test that SecureBoot requires UEFI mode."""
        await self._setup_test_db()
        
        from hawkfish_controller.services.bios import bios_service
        
        # Should raise error when trying to enable SecureBoot with LegacyBios
        attributes = {
            "BootMode": "LegacyBios",
            "SecureBoot": "Enabled"
        }
        
        from hawkfish_controller.services.bios import BiosValidationError
        
        with pytest.raises(BiosValidationError) as exc_info:
            await bios_service.stage_bios_changes(
                "test-system", attributes, "OnReset", "test-user"
            )
        
        assert "SecureBoot can only be enabled when BootMode is set to Uefi" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_apply_pending_bios_changes(self):
        """Test applying pending BIOS changes."""
        await self._setup_test_db()
        
        from hawkfish_controller.services.bios import bios_service
        
        # Stage some changes first
        attributes = {"BootMode": "LegacyBios"}
        await bios_service.stage_bios_changes(
            "test-system", attributes, "OnReset", "test-user"
        )
        
        # Apply changes
        applied = await bios_service.apply_pending_bios_changes("test-system")
        assert applied is not None
        assert applied["BootMode"] == "LegacyBios"
        
        # Verify no longer pending
        pending = await bios_service.get_pending_bios_changes("test-system")
        assert pending is None
