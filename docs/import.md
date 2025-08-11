### Import / Adopt

Endpoints:
- `GET /redfish/v1/Oem/HawkFish/Import/Scan` → lists candidate domains
- `POST /redfish/v1/Oem/HawkFish/Import/Adopt?dry_run=false` with body `{ "Domains": [{"Name":"vm1"}] }`

Notes:
- Current implementation assumes adoption without persistence, intended for future inventory mapping


