from pathlib import Path

from fastapi.testclient import TestClient

from hawkfish_controller.api import managers as managers_api
from hawkfish_controller.api import systems as systems_api
from hawkfish_controller.main_app import create_app


class FakeDriver:
    def __init__(self) -> None:
        self.powered_on = False
        self.boot_target = None
        self.iso_attached = False

    def list_systems(self):
        return [{"Id": "node01"}]

    def get_system(self, system_id: str):
        return {"Id": system_id, "Name": system_id}

    def reset_system(self, system_id: str, reset_type: str) -> None:
        self.powered_on = reset_type.lower() in {"on", "forceon", "forcerestart"}

    def set_boot_override(self, system_id: str, target: str, persist: bool = False) -> None:  # noqa: ARG002
        self.boot_target = target

    def attach_iso(self, system_id: str, image_path_or_url: str) -> None:
        self.iso_attached = True

    def detach_iso(self, system_id: str) -> None:
        self.iso_attached = False


def test_e2e_power_boot_media_flow(tmp_path: Path):
    # force state/iso to temp for permissions
    from hawkfish_controller.config import settings
    import os

    state_dir = tmp_path / "state"
    iso_dir = tmp_path / "isos"
    
    # Create directories
    os.makedirs(state_dir, exist_ok=True)
    os.makedirs(iso_dir, exist_ok=True)
    
    settings.state_dir = str(state_dir)
    settings.iso_dir = str(iso_dir)
    
    # Initialize database tables for testing
    import asyncio
    from hawkfish_controller.services.projects import project_store
    
    # Update project store to use the temp directory
    project_store.db_path = str(state_dir / "hawkfish.db")
    
    async def init_test_db():
        await project_store.init()
    
    asyncio.run(init_test_db())
    
    # Also update the bios service to use the same database
    from hawkfish_controller.services.bios import bios_service
    bios_service.db_path = str(state_dir / "hawkfish.db")
    
    app = create_app()
    fake = FakeDriver()
    app.dependency_overrides[systems_api.get_driver] = lambda: fake
    app.dependency_overrides[managers_api.get_driver] = lambda: fake
    client = TestClient(app)

    # list systems
    r = client.get("/redfish/v1/Systems")
    assert r.status_code == 200

    # set boot to cd
    r = client.patch("/redfish/v1/Systems/node01", json={"Boot": {"BootSourceOverrideTarget": "CD", "BootSourceOverrideEnabled": "Once"}})
    assert r.status_code == 200

    # attach local ISO
    r = client.post(
        "/redfish/v1/Managers/HawkFish/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia",
        json={"SystemId": "node01", "Image": str(tmp_path / "fake.iso"), "Inserted": True},
    )
    # immediate success because local path
    assert r.status_code == 200

    # power on
    r = client.post("/redfish/v1/Systems/node01/Actions/ComputerSystem.Reset", json={"ResetType": "On"})
    assert r.status_code == 200


