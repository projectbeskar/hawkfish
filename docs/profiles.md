### Profiles

Endpoint: `/redfish/v1/Oem/HawkFish/Profiles`

Body example for create:
```json
{
  "Name": "small-linux",
  "CPU": 2,
  "MemoryMiB": 2048,
  "DiskGiB": 20,
  "Network": "default",
  "Boot": {"Primary": "Hdd"},
  "Image": {"url": "https://example/base.qcow2"}
}
```

Notes:
- Validates input via JSON Schema
- `Name` is used as profile id


