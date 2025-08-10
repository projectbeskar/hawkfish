### HawkFish

A fully virtual “bare-metal” lab that uses Linux KVM/libvirt to emulate hardware and exposes a DMTF Redfish API for provisioning, power control, boot media, and events.

### Quickstart (dev)

- Requirements: Linux host with Python 3.11+, optional libvirt/KVM for full functionality.
- Install (without libvirt bindings):

```bash
python -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e .[dev]
```

- Run controller:

```bash
python -m hawkfish_controller --host 0.0.0.0 --port 8080
```

- Check ServiceRoot:

```bash
curl -s http://localhost:8080/redfish/v1/ | jq .
```

See `docs/quickstart.md` for enabling KVM/libvirt and more.

License: Apache-2.0


