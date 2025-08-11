### Durable Event Delivery

HawkFish implements durable webhook delivery with retry logic and dead letter handling.

#### Architecture

Events are queued in an outbound table and processed by a background worker:

1. **Event Publication**: Events are queued for matching subscriptions
2. **Background Worker**: Processes queue with exponential backoff
3. **Retry Logic**: Up to 5 attempts with 2^n second delays
4. **Dead Letters**: Failed deliveries after max attempts

#### Database Tables

- `hf_outbox`: Pending webhook deliveries
- `hf_deadletters`: Failed deliveries after max attempts

#### Configuration

Environment variables:
- `HF_EVENTS_MAX_ATTEMPTS`: Maximum retry attempts (default: 5)
- `HF_EVENTS_WORKERS`: Worker concurrency (default: 1)

#### HMAC Signing

When a subscription includes a `Secret`, payloads are signed:

```
X-HawkFish-Signature: sha256=<hex-digest>
```

The signature is computed over the JSON payload using HMAC-SHA256.

#### Monitoring

The outbox queue depth and delivery metrics can be monitored via:
- Database queries on `hf_outbox` table
- Prometheus metrics (if enabled)

#### Deterministic Testing

For tests, event delivery remains deterministic through immediate queue processing.
