### Quickstart

Prereqs:
- Ubuntu/Debian/Fedora host
- Python 3.11+
- Optional for full functionality: libvirt and KVM

Install dev environment (without libvirt bindings):
```bash
python -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e .[dev]
```

Run controller:
```bash
python -m hawkfish_controller --host 0.0.0.0 --port 8080
```

Check Redfish ServiceRoot:
```bash
curl -s http://localhost:8080/redfish/v1/ | jq .
```

CLI quickstart:
```bash
python -m hawkfish_cli login --url http://localhost:8080/redfish/v1 --username admin
python -m hawkfish_cli systems
python -m hawkfish_cli systems-show node01
python -m hawkfish_cli boot node01 --set cd --persist
python -m hawkfish_cli media-insert node01 --image /var/lib/hawkfish/isos/some.iso
python -m hawkfish_cli tasks
python -m hawkfish_cli task-watch <taskId>
python -m hawkfish_cli events-sse
```

Enable libvirt on Ubuntu (optional):
```bash
sudo apt-get update
sudo apt-get install -y qemu-kvm libvirt-daemon-system libvirt-clients
sudo adduser "$USER" libvirt
newgrp libvirt
```

Install libvirt Python bindings:
```bash
. .venv/bin/activate
pip install -e .[virt]
```

Now `GET /redfish/v1/Systems` will reflect your libvirt domains.


