### Events

SSE endpoint: GET /events/stream

Message format:

id: <uuid>
event: <EventType>
data: {"time":"<RFC3339>", ...}

Webhook subscriptions:

POST /redfish/v1/EventService/Subscriptions
Body: {"Destination":"https://example","EventTypes":["PowerStateChanged","TaskUpdated",...]}


