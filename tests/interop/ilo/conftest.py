"""
Pytest fixtures for HPE iLO interoperability tests.
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
    """Create test client with HPE persona enabled."""
    app = create_app()
    
    # Override the libvirt driver with fake driver
    from hawkfish_controller.drivers.libvirt_driver import get_driver
    
    def get_fake_driver():
        return FakeDriver()
    
    app.dependency_overrides[get_driver] = get_fake_driver
    
    return TestClient(app)


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
    global_session_store.sessions["test-admin-token"] = session
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
    global_session_store.sessions["test-operator-token"] = session
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
def ilo_enabled():
    """Check if iLO persona testing is enabled."""
    return os.environ.get("HF_TEST_PERSONA", "").lower() == "hpe_ilo5"


@pytest.fixture
def skip_if_ilo_disabled(ilo_enabled):
    """Skip test if iLO persona testing is not enabled."""
    if not ilo_enabled:
        pytest.skip("HPE iLO persona testing not enabled (set HF_TEST_PERSONA=hpe_ilo5)")


@pytest.fixture(autouse=True)
def setup_test_persona(client, admin_headers, test_system_id):
    """Set up test system with HPE iLO5 persona."""
    # Set the system persona to hpe_ilo5 for testing
    client.patch(
        f"/redfish/v1/Oem/HawkFish/Personas/Systems/{test_system_id}",
        json={"persona": "hpe_ilo5"},
        headers=admin_headers
    )
    # Don't fail if persona setting fails in setup
    yield
    
    # Cleanup - remove persona override
    try:
        client.delete(
            f"/redfish/v1/Oem/HawkFish/Personas/Systems/{test_system_id}",
            headers=admin_headers
        )
    except Exception:
        pass  # Ignore cleanup failures
