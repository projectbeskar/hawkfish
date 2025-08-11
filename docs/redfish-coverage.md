### Redfish Coverage (snapshot)

- ServiceRoot: GET ✓ (Links ✓)
- Systems: GET collection ✓, GET item ✓ (ETag ✓), PATCH Boot override ✓ (If-Match ✓)
- Actions: ComputerSystem.Reset (On, GracefulShutdown, ForceOff, ForceRestart) ✓
- Managers/VirtualMedia: collection/item ✓, Insert/Eject ✓ (local + URL download ✓)
- Sessions: session service and token issuance ✓ (RBAC enforced)
- TaskService: list/get ✓, background tasks ✓
- EventService: SSE ✓, webhook subscriptions ✓
- Chassis: single chassis ✓


