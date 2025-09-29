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
        # Initialize database in temp directory
        import asyncio
        from hawkfish_controller.services.projects import project_store
        
        # Update all service database paths
        project_store.db_path = os.path.join(temp_dir, "hawkfish.db")
        
        # Update bios service database path
        from hawkfish_controller.services.bios import bios_service
        bios_service.db_path = os.path.join(temp_dir, "hawkfish.db")
        
        # Update all service database paths
        from hawkfish_controller.services.persona import persona_service
        persona_service.db_path = os.path.join(temp_dir, "hawkfish.db")
        
        # Note: Task service paths will be handled via dependency injection
        
        async def init_test_db():
            await project_store.init()
            # Initialize BIOS service tables manually
            from hawkfish_controller.services.bios import bios_service
            import aiosqlite
            async with aiosqlite.connect(bios_service.db_path) as db:
                # Create BIOS tables with correct schema matching projects.py
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS hf_bios_pending (
                        system_id TEXT PRIMARY KEY,
                        attributes TEXT NOT NULL,
                        apply_time TEXT NOT NULL,
                        staged_at TEXT NOT NULL,
                        staged_by TEXT
                    )
                """)
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS hf_bios_applied (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        system_id TEXT NOT NULL,
                        attributes TEXT NOT NULL,
                        applied_at TEXT NOT NULL,
                        applied_by TEXT
                    )
                """)
                await db.commit()
        
        asyncio.run(init_test_db())
        
        # Override the global task service singleton BEFORE creating the app
        from hawkfish_controller.services.tasks import TaskService
        from hawkfish_controller.api import task_event
        
        # Replace the global singleton with test instance
        task_event._task_service = TaskService(db_path=os.path.join(temp_dir, "hawkfish.db"))
        
        app = create_app()
        
        # Override the libvirt driver with fake driver in all modules that use it
        from hawkfish_controller.drivers.libvirt_driver import get_driver as libvirt_get_driver
        from hawkfish_controller.api.systems import get_driver as systems_get_driver
        from hawkfish_controller.api.managers import get_driver as managers_get_driver
        
        def get_fake_driver():
            return FakeDriver()
        
        app.dependency_overrides[libvirt_get_driver] = get_fake_driver
        app.dependency_overrides[systems_get_driver] = get_fake_driver
        app.dependency_overrides[managers_get_driver] = get_fake_driver
        
        # Also override dependency injection functions
        from hawkfish_controller.api.orchestrator import get_task_service
        from hawkfish_controller.api.batch import get_task_service as get_batch_task_service
        from hawkfish_controller.api.task_event import get_task_service as get_event_task_service
        
        def get_test_task_service():
            return task_event._task_service  # Use same instance
        
        app.dependency_overrides[get_task_service] = get_test_task_service
        app.dependency_overrides[get_batch_task_service] = get_test_task_service
        app.dependency_overrides[get_event_task_service] = get_test_task_service
        
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
