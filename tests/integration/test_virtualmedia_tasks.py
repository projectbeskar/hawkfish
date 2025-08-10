import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from fastapi.testclient import TestClient

from hawkfish_controller.api import managers as managers_api
from hawkfish_controller.api import systems as systems_api
from hawkfish_controller.config import settings
from hawkfish_controller.main_app import create_app


class FakeDriver:
    def __init__(self) -> None:
        self.attached: list[tuple[str, str]] = []
        self.detached: list[str] = []

    def list_systems(self):
        return [{"Id": "node01"}]

    def get_system(self, system_id: str):
        return {"Id": system_id, "Name": system_id}

    def reset_system(self, system_id: str, reset_type: str) -> None:  # noqa: ARG002
        return None

    def set_boot_override(self, system_id: str, target: str, persist: bool = False) -> None:  # noqa: ARG002
        return None

    def attach_iso(self, system_id: str, image_path_or_url: str) -> None:
        self.attached.append((system_id, image_path_or_url))

    def detach_iso(self, system_id: str) -> None:
        self.detached.append(system_id)


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    _, port = s.getsockname()
    s.close()
    return int(port)


class IsoHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = b"FAKEISO\n" * 1024
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A003
        return


def test_virtual_media_insert_url(tmp_path: Path, monkeypatch):
    # point state/iso dirs to tmp
    settings.state_dir = str(tmp_path / "state")
    settings.iso_dir = str(tmp_path / "isos")
    os.makedirs(settings.iso_dir, exist_ok=True)

    app = create_app()
    fake = FakeDriver()
    app.dependency_overrides[managers_api.get_driver] = lambda: fake
    app.dependency_overrides[systems_api.get_driver] = lambda: fake
    client = TestClient(app)

    port = _free_port()
    server = HTTPServer(("127.0.0.1", port), IsoHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    url = f"http://127.0.0.1:{port}/tiny.iso"
    r = client.post(
        "/redfish/v1/Managers/HawkFish/VirtualMedia/Cd/Actions/VirtualMedia.InsertMedia",
        json={"SystemId": "node01", "Image": url, "Inserted": True},
    )
    assert r.status_code == 202
    task_uri = r.headers["Location"]

    # poll task until completed
    for _ in range(100):
        tr = client.get(task_uri)
        if tr.status_code == 200 and tr.json().get("TaskState") == "Completed":
            break
    else:
        raise AssertionError("Task did not complete")

    # index updated
    index_path = Path(settings.iso_dir) / "index.json"
    assert index_path.exists()
    data = json.loads(index_path.read_text())
    assert data.get("images")
    # driver attach called
    assert any(sys == "node01" for sys, _ in fake.attached)


