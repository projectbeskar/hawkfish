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
# Profiles & Batch
python -m hawkfish_cli profiles
python -m hawkfish_cli profile-create small-linux --cpu 2 --memory 2048 --disk 20 --network default --boot-primary hdd
python -m hawkfish_cli batch-create small-linux --count 3 --name-prefix node --start-index 1 --zero-pad 2
# Import & Subscriptions
python -m hawkfish_cli import-scan
python -m hawkfish_cli subs-create https://localhost:9000/webhook --event-types PowerStateChanged,MediaInserted --system-ids node01 --secret mysecret
# Host Pools, Images & Network Profiles
python -m hawkfish_cli hosts
python -m hawkfish_cli host-add qemu+ssh://user@host/system "Remote Host" --labels env=prod,ssd=true
python -m hawkfish_cli images
python -m hawkfish_cli image-add ubuntu 22.04 --url https://example.com/ubuntu.img --sha256 abc123...
python -m hawkfish_cli netprofiles
python -m hawkfish_cli netprofile-create production --libvirt-network default --count 2
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


