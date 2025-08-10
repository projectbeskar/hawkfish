from fastapi.testclient import TestClient

from hawkfish_controller.main_app import create_app


def test_systems_empty(monkeypatch):
    app = create_app()
    client = TestClient(app)

    resp = client.get("/redfish/v1/Systems")
    assert resp.status_code == 200
    body = resp.json()
    assert body["Members@odata.count"] == 0
    assert body["Members"] == []


