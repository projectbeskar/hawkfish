# HawkFish Docker Compose Deployment

This directory contains a Docker Compose configuration for deploying HawkFish in a single-host environment.

## Quick Start

1. **Ensure libvirt is running** (if using local virtualization):
   ```bash
   sudo systemctl enable --now libvirtd
   sudo usermod -a -G libvirt $USER
   # Log out and back in for group changes to take effect
   ```

2. **Configure environment** (optional):
   ```bash
   cp .env.example .env
   # Edit .env with your specific configuration
   ```

3. **Start HawkFish**:
   ```bash
   docker-compose up -d
   ```

4. **Access the interface**:
   - API: http://localhost:8080/redfish/v1/
   - Web UI: http://localhost:8080/ui/ (if `HF_UI_ENABLED=true`)
   - OpenAPI docs: http://localhost:8080/docs

## Configuration

### Environment Variables

All HawkFish configuration can be provided via environment variables in the `docker-compose.yml` or `.env` file:

- `LIBVIRT_URI`: Libvirt connection URI (default: `qemu:///system`)
- `HF_AUTH`: Authentication mode (`none` for dev, `sessions` for production)
- `HF_UI_ENABLED`: Enable web UI (`true`/`false`)
- `HF_STATE_DIR`: State directory inside container (default: `/var/lib/hawkfish`)

### Libvirt Connection

#### Local Libvirt (same host)
Uncomment the libvirt socket mount in `docker-compose.yml`:
```yaml
volumes:
  - /var/run/libvirt/libvirt-sock:/var/run/libvirt/libvirt-sock
```

#### Remote Libvirt
Set `LIBVIRT_URI` to a remote URI:
```yaml
environment:
  LIBVIRT_URI: "qemu+ssh://user@hypervisor/system"
```

#### Multiple Hosts
Use the HawkFish hosts API to register multiple libvirt hosts:
```bash
# Add a host via API
curl -X POST http://localhost:8080/redfish/v1/Oem/HawkFish/Hosts \
  -H "Content-Type: application/json" \
  -d '{"URI": "qemu+ssh://host1/system", "Name": "host1", "Labels": {"region": "us-west"}}'
```

### TLS Configuration

#### Self-signed TLS (development)
```yaml
environment:
  HF_DEV_TLS: "self-signed"
```

#### Custom TLS certificates
```yaml
environment:
  HF_DEV_TLS: "custom"
  HF_TLS_CERT: "/etc/hawkfish/certs/server.crt"
  HF_TLS_KEY: "/etc/hawkfish/certs/server.key"
volumes:
  - ./certs:/etc/hawkfish/certs:ro
```

### Persistent Data

HawkFish stores metadata in SQLite databases and cached images in the state directory. The compose configuration uses a named volume (`hawkfish-state`) for persistence.

To backup the state:
```bash
docker run --rm -v hawkfish_hawkfish-state:/data -v $(pwd):/backup alpine \
  tar czf /backup/hawkfish-backup-$(date +%Y%m%d).tar.gz -C /data .
```

## Security Considerations

The default configuration includes security hardening:
- Runs as non-root user (UID 1000)
- Read-only filesystem
- Dropped capabilities
- No new privileges

For production deployment:
- Use `HF_AUTH=sessions` for authentication
- Configure TLS with proper certificates
- Use secrets management for sensitive configuration
- Consider network isolation and firewall rules

## Monitoring

### Health Checks
The service includes health checks that verify API availability:
```bash
docker-compose ps  # Check health status
```

### Logs
```bash
docker-compose logs -f hawkfish  # Follow logs
```

### Metrics
HawkFish exposes Prometheus metrics:
```bash
curl http://localhost:8080/redfish/v1/metrics
curl http://localhost:8080/redfish/v1/libvirt-pool-metrics
```

## Troubleshooting

### Common Issues

1. **Permission denied accessing libvirt**:
   - Ensure user is in `libvirt` group
   - Check libvirt socket permissions
   - Verify `LIBVIRT_URI` is correct

2. **Container won't start**:
   ```bash
   docker-compose logs hawkfish
   ```

3. **Cannot connect to remote libvirt**:
   - Test SSH connectivity: `ssh user@hypervisor`
   - Verify libvirt is running on remote host
   - Check firewall rules

4. **Web UI not loading**:
   - Ensure `HF_UI_ENABLED=true`
   - Check if UI build exists in container
   - Verify container has write access to state directory

### Development Mode

For development with live code changes:
```bash
# Mount source code for development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## Scaling

For multi-node deployments, consider:
- External PostgreSQL database instead of SQLite
- Shared storage for images and state
- Load balancer for multiple controller instances
- Message queue for distributed event delivery
