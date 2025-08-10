from fastapi.testclient import TestClient

from hawkfish_controller.main_app import create_app


def test_service_root_ok():
    app = create_app()
    client = TestClient(app)
    resp = client.get("/redfish/v1/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["Id"] == "RootService"
    assert body["Links"]["Systems"]["@odata.id"] == "/redfish/v1/Systems"


