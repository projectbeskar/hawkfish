### Events

SSE endpoint: GET /events/stream

Message format:

id: <uuid>
event: <EventType>
data: {"time":"<RFC3339>", ...}

Webhook subscriptions:

POST /redfish/v1/EventService/Subscriptions
Body: {"Destination":"https://example","EventTypes":["PowerStateChanged","TaskUpdated",...],"SystemIds":["node01"],"Secret":"<optional>"}

Filters and signing:
- EventTypes: optional filter by event types
- SystemIds: optional filter by specific `systemId`
- Secret: when set, payloads are signed with header `X-HawkFish-Signature: sha256=<hex>` over the JSON body


