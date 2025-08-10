from fastapi.testclient import TestClient

from hawkfish_controller.main_app import create_app


def test_session_create():
    app = create_app()
    client = TestClient(app)
    r = client.post("/redfish/v1/SessionService/Sessions", json={"UserName": "alice"})
    assert r.status_code == 200
    tok = r.json()["X-Auth-Token"]
    assert tok


