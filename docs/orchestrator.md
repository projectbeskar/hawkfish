### Orchestrator

Create a node:

POST /redfish/v1/Systems
Body: {"Name":"node01","CPU":2,"MemoryMiB":4096,"DiskGiB":20,"Image":{"url":"http://.../base.qcow2"}}
Returns 202 with Location to Task.

Delete a node:

DELETE /redfish/v1/Systems/{id}?delete_storage=true
Returns 202 with Location to Task.


