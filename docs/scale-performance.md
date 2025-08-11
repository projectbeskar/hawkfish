### Scale & Performance

HawkFish includes several features to handle larger deployments and higher request volumes.

#### Pagination & Filtering

**Collection Pagination:**
- **Default Page Size**: 50 items per page
- **Query Parameters**: `?page=1&per_page=100`
- **Navigation Links**: `@odata.nextLink` and `@odata.prevLink` in responses
- **Total Count**: `Members@odata.count` shows page size, not total

**Supported Collections:**
- `GET /redfish/v1/Systems` - Systems with power state filtering
- `GET /redfish/v1/Oem/HawkFish/Profiles` - Node profiles
- `GET /redfish/v1/Oem/HawkFish/Images` - Image catalog
- `GET /redfish/v1/Oem/HawkFish/Hosts` - Host pools

**Filtering Syntax:**
```
# Filter by power state
GET /redfish/v1/Systems?filter=power:on

# Filter by host (when host metadata available)
GET /redfish/v1/Systems?filter=host:production-host-1

# Multiple filters
GET /redfish/v1/Systems?filter=power:on,host:prod
```

#### Rate Limiting

**Token Bucket Algorithm:**
- **Default Limits**: 100 requests per minute per client IP
- **Burst Capacity**: Full bucket capacity available immediately
- **Refill Rate**: 100 tokens per 60 seconds (1.67/second)
- **Granularity**: Per-client IP address

**HTTP Headers:**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1699123456
Retry-After: 60  # (when rate limited)
```

**Rate Limit Responses:**
```json
{
  "error": {
    "code": "Base.1.0.GeneralError",
    "message": "Rate limit exceeded",
    "@Message.ExtendedInfo": [{
      "MessageId": "Base.1.0.RateLimitExceeded",
      "Message": "The request rate limit has been exceeded.",
      "Severity": "Warning"
    }]
  }
}
```

**Configuration:**
- **Development Mode**: Rate limiting disabled when `auth_mode=none`
- **Production**: Enabled by default with configurable limits
- **Bypass Endpoints**: ServiceRoot and metrics endpoints excluded

#### Libvirt Connection Pooling

**Connection Management:**
- **Per-Host Pools**: Separate connection pools for each libvirt host
- **Connection Reuse**: Persistent connections across multiple requests
- **Pool Sizing**: Bounded pool size to prevent resource exhaustion
- **Health Monitoring**: Automatic connection health checks and recovery

**Performance Benefits:**
- **Reduced Latency**: Eliminates connection setup overhead
- **Higher Throughput**: Concurrent operations across multiple connections
- **Resource Efficiency**: Optimal connection utilization

#### Metrics & Monitoring

**Performance Metrics:**
```
# Request metrics
hawkfish_requests_total{path,method,status}
hawkfish_request_latency_seconds{path,method}

# Rate limiting metrics  
hawkfish_rate_limit_hits_total{client_ip}
hawkfish_rate_limit_blocks_total{client_ip}

# Connection pool metrics
hawkfish_libvirt_connections_active{host}
hawkfish_libvirt_connections_idle{host}

# Pagination metrics
hawkfish_collection_page_requests_total{collection,page_size}
```

**Health Indicators:**
- **Response Times**: 95th percentile latency tracking
- **Error Rates**: 4xx/5xx response ratios
- **Resource Utilization**: Connection pool usage
- **Queue Depths**: Rate limiting queue sizes

#### Load Testing

**Stress Test Markers:**
```bash
# Run load tests (if implemented)
pytest -m stress --maxfail=1

# Create N systems (fake driver)
pytest tests/stress/test_scale.py::test_create_many_systems

# Pagination performance
pytest tests/stress/test_pagination.py::test_large_collections
```

**Performance Targets:**
- **Single System Operations**: < 100ms p95
- **Collection Listings**: < 500ms p95 (paginated)
- **Power Actions**: < 2s p95 (including libvirt calls)
- **Concurrent Requests**: 50 req/sec sustained

#### Optimization Tips

**Client-Side:**
1. **Use Pagination**: Don't fetch large collections without pagination
2. **Respect Rate Limits**: Implement exponential backoff on 429 responses
3. **Cache Responses**: Use ETags for conditional requests
4. **Batch Operations**: Use batch APIs where available

**Server-Side:**
1. **Connection Pooling**: Configure appropriate pool sizes for your deployment
2. **Rate Limit Tuning**: Adjust limits based on client patterns
3. **Resource Monitoring**: Monitor memory/CPU usage under load
4. **Database Optimization**: SQLite performance tuning for high concurrency

**Deployment:**
1. **Horizontal Scaling**: Multiple controller instances behind load balancer
2. **Database Separation**: Dedicated storage for high-throughput workloads
3. **Network Optimization**: Low-latency networking to libvirt hosts
4. **Resource Allocation**: Adequate CPU/memory for concurrent operations
