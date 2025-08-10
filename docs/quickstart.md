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


