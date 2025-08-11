import hashlib
import hmac
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from fastapi.testclient import TestClient

from hawkfish_controller.api.task_event import get_subs
from hawkfish_controller.main_app import create_app


class WebhookHandler(BaseHTTPRequestHandler):
    secret = b"testsecret"
    received = []

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        sig = self.headers.get("X-HawkFish-Signature", "")
        digest = hmac.new(self.secret, body, hashlib.sha256).hexdigest()
        assert sig == f"sha256={digest}"
        payload = json.loads(body)
        self.__class__.received.append(payload)
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):  # noqa: A003
        return


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    _, port = s.getsockname()
    s.close()
    return int(port)


def test_event_webhook_filters_and_signature(tmp_path, monkeypatch):
    app = create_app()
    client = TestClient(app)

    port = _free_port()
    server = HTTPServer(("127.0.0.1", port), WebhookHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    dest = f"http://127.0.0.1:{port}/hook"
    subs = get_subs()

    # Create subscription via API with filter and secret
    r = client.post(
        "/redfish/v1/EventService/Subscriptions",
        json={"Destination": dest, "EventTypes": ["PowerStateChanged"], "SystemIds": ["node01"], "Secret": "testsecret"},
    )
    assert r.status_code == 200

    # Publish events: only one should be delivered
    import anyio

    from hawkfish_controller.services.events import publish_event

    anyio.run(publish_event, "PowerStateChanged", {"systemId": "node01"}, subs)
    anyio.run(publish_event, "PowerStateChanged", {"systemId": "node02"}, subs)

    # Wait briefly for async delivery
    import time

    for _ in range(50):
        if WebhookHandler.received:
            break
        time.sleep(0.1)

    assert len(WebhookHandler.received) == 1
    assert WebhookHandler.received[0]["systemId"] == "node01"


