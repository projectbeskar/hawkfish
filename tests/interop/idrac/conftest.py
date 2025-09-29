"""
Pytest fixtures for Dell iDRAC interoperability tests.
"""

import os
import pytest
from fastapi.testclient import TestClient

from hawkfish_controller.main_app import create_app
from hawkfish_controller.api.sessions import global_session_store
from hawkfish_controller.services.sessions import Session
from hawkfish_controller.drivers.fake_driver import FakeDriver


@pytest.fixture
def client():
    """Create test client with Dell persona enabled."""
    import tempfile
    import os
    
    # Create temporary directory for test state
    temp_dir = tempfile.mkdtemp()
    
    # Override the settings to use the temp directory
    from hawkfish_controller.config import settings
    original_state_dir = settings.state_dir
    original_iso_dir = settings.iso_dir
    settings.state_dir = temp_dir
    settings.iso_dir = os.path.join(temp_dir, "isos")
    
    # Ensure directories exist
    os.makedirs(settings.state_dir, exist_ok=True)
    os.makedirs(settings.iso_dir, exist_ok=True)
    
    try:
        app = create_app()
        
        # Override the libvirt driver with fake driver
        from hawkfish_controller.drivers.libvirt_driver import get_driver
        
        def get_fake_driver():
            return FakeDriver()
        
        app.dependency_overrides[get_driver] = get_fake_driver
        
        yield TestClient(app)
    finally:
        # Restore original settings
        settings.state_dir = original_state_dir
        settings.iso_dir = original_iso_dir
        
        # Clean up temp directory
        import shutil
        try:
            shutil.rmtree(temp_dir)
        except Exception:
            pass


@pytest.fixture
def admin_session():
    """Create admin session for testing."""
    import time
    now = time.time()
    session = Session(
        token="test-admin-token",
        username="test-admin", 
        role="admin",
        created_at=now,
        expires_at=now + 3600,  # 1 hour
        last_activity=now
    )
    global_session_store._token_to_session["test-admin-token"] = session
    return session


@pytest.fixture
def operator_session():
    """Create operator session for testing."""
    import time
    now = time.time()
    session = Session(
        token="test-operator-token",
        username="test-operator",
        role="operator", 
        created_at=now,
        expires_at=now + 3600,  # 1 hour
        last_activity=now
    )
    global_session_store._token_to_session["test-operator-token"] = session
    return session


@pytest.fixture
def admin_headers(admin_session):
    """Get headers for admin authentication."""
    return {"X-Auth-Token": admin_session.token}


@pytest.fixture
def operator_headers(operator_session):
    """Get headers for operator authentication."""
    return {"X-Auth-Token": operator_session.token}


@pytest.fixture
def test_system_id():
    """Standard test system ID."""
    return "test-vm-001"


@pytest.fixture
def idrac_enabled():
    """Check if iDRAC persona testing is enabled."""
    return os.environ.get("HF_TEST_PERSONA", "").lower() == "dell_idrac9"


@pytest.fixture
def skip_if_idrac_disabled(idrac_enabled):
    """Skip test if iDRAC persona testing is not enabled."""
    if not idrac_enabled:
        pytest.skip("Dell iDRAC persona testing not enabled (set HF_TEST_PERSONA=dell_idrac9)")


@pytest.fixture(autouse=True)
def setup_test_persona(client, admin_headers, test_system_id):
    """Set up test system with Dell iDRAC9 persona."""
    # Try to set the system persona to dell_idrac9 for testing, but don't fail if it doesn't work
    try:
        response = client.patch(
            f"/redfish/v1/Oem/HawkFish/Personas/Systems/{test_system_id}",
            json={"persona": "dell_idrac9"},
            headers=admin_headers
        )
        if response.status_code not in (200, 201, 202):
            print(f"Warning: Could not set persona (status {response.status_code}), continuing anyway")
    except Exception as e:
        print(f"Warning: Could not set persona ({e}), continuing anyway")
    
    yield
    
    # Cleanup - remove persona override
    try:
        client.delete(
            f"/redfish/v1/Oem/HawkFish/Personas/Systems/{test_system_id}",
            headers=admin_headers
        )
    except Exception:
        pass  # Ignore cleanup failures
