### Architecture (v0)

- hawkfish-controller: FastAPI app exposing Redfish resources
- hawkfish-virt: libvirt driver translating Redfish ops to libvirt

For v0, state lives in libvirt and in-memory. SQLite-backed TaskService will be added later.


