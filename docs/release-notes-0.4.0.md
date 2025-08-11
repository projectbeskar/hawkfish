### HawkFish v0.4.0

Highlights:
- Profiles: reusable node specs with JSON Schema validation
- Batch provisioning: create N nodes from a profile with concurrency control
- PXE helper endpoints and BootToPXE action
- Import/Adopt endpoints for existing libvirt domains
- EventService: webhook filters (types/system) + HMAC signing, SSE maintained
- CLI: profiles, batch, import, subscriptions added
- Docs updated (quickstart, events, profiles, batch, import)

Quality:
- Deterministic event delivery for tests, DB migrations with fallback
- Lint/type clean; tests green


