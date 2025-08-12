from fastapi.testclient import TestClient

from hawkfish_controller.main_app import create_app
from hawkfish_controller.api import systems as systems_api


class FakeDriver:
    """Mock libvirt driver for testing."""
    
    def list_systems(self):
        return []
    
    def get_system(self, system_id: str):
        return None


def test_systems_empty(monkeypatch):
    app = create_app()
    fake = FakeDriver()
    app.dependency_overrides[systems_api.get_driver] = lambda: fake
    client = TestClient(app)

    resp = client.get("/redfish/v1/Systems")
    assert resp.status_code == 200
    body = resp.json()
    assert body["Members@odata.count"] == 0
    assert body["Members"] == []


