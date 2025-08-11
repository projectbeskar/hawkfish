### Batch Provisioning

Endpoint: `POST /redfish/v1/Oem/HawkFish/Batches`

Body:
```json
{
  "NamePrefix": "node",
  "StartIndex": 1,
  "ZeroPad": 2,
  "Count": 3,
  "ProfileId": "small-linux",
  "MaxConcurrency": 3
}
```

Behavior:
- Creates asynchronous task; response contains the task URI
- Applies profile to each node; names like `node01`, `node02`, ...


