# HawkFish Deployment Guide

This guide covers various deployment options for HawkFish, from development setups to production environments.

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -e .

# Start HawkFish
export HF_AUTH=none
export HF_UI_ENABLED=true
python -m hawkfish_controller
```

Access at: http://localhost:8080/ui/

### Docker Compose

```bash
# Clone repository
git clone https://github.com/projectbeskar/hawkfish.git
cd hawkfish/deploy/compose/

# Start services
docker-compose up -d

# View logs
docker-compose logs -f hawkfish
```

### Kubernetes (Helm)

```bash
# Add Helm repository (when published)
helm repo add hawkfish https://projectbeskar.github.io/hawkfish

# Install
helm install hawkfish hawkfish/hawkfish \
  --set hawkfish.auth.mode=sessions \
  --set persistence.enabled=true
```

## Deployment Methods

### 1. Docker Compose

**Use case**: Single-host development, small production deployments

#### Basic Setup

```yaml
# docker-compose.yml
version: '3.8'
services:
  hawkfish:
    image: hawkfish/hawkfish-controller:latest
    ports:
      - "8080:8080"
    environment:
      HF_AUTH: "sessions"
      HF_UI_ENABLED: "true"
      LIBVIRT_URI: "qemu:///system"
    volumes:
      - hawkfish-state:/var/lib/hawkfish
      - /var/run/libvirt/libvirt-sock:/var/run/libvirt/libvirt-sock
    restart: unless-stopped

volumes:
  hawkfish-state:
```

#### Advanced Configuration

```yaml
services:
  hawkfish:
    image: hawkfish/hawkfish-controller:latest
    ports:
      - "8443:8443"
    environment:
      # API Configuration
      HF_API_HOST: "0.0.0.0"
      HF_API_PORT: "8443"
      
      # Authentication
      HF_AUTH: "sessions"
      HF_DEV_TLS: "self-signed"
      
      # Libvirt
      LIBVIRT_URI: "qemu+ssh://hypervisor/system"
      HF_LIBVIRT_POOL_MIN: "2"
      HF_LIBVIRT_POOL_MAX: "20"
      
      # Features
      HF_UI_ENABLED: "true"
    volumes:
      - hawkfish-state:/var/lib/hawkfish
      - ./certs:/etc/hawkfish/certs:ro
    secrets:
      - hawkfish-tls-cert
      - hawkfish-tls-key
    healthcheck:
      test: ["CMD", "curl", "-f", "https://localhost:8443/redfish/v1/"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 2. Kubernetes (Helm)

**Use case**: Container orchestration, scalable deployments

#### Installation

```bash
# Install from local chart
helm install hawkfish charts/hawkfish/ \
  --values my-values.yaml \
  --namespace hawkfish \
  --create-namespace
```

#### Values Configuration

```yaml
# my-values.yaml
replicaCount: 1

image:
  repository: hawkfish/hawkfish-controller
  tag: "0.7.0"

hawkfish:
  auth:
    mode: "sessions"
  tls:
    mode: "custom"
    secretName: "hawkfish-tls"
  libvirt:
    uri: "qemu+ssh://hypervisor.example.com/system"
    pool:
      min: 2
      max: 20
  ui:
    enabled: true

persistence:
  enabled: true
  size: 20Gi
  storageClass: "fast-ssd"

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: hawkfish.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: hawkfish-tls
      hosts:
        - hawkfish.example.com

resources:
  limits:
    cpu: 2000m
    memory: 1Gi
  requests:
    cpu: 500m
    memory: 512Mi
```

#### Multi-Host Configuration

```yaml
hawkfish:
  # Pre-configure multiple libvirt hosts
  hosts:
    - uri: "qemu+ssh://host1.example.com/system"
      name: "host1"
      labels:
        region: "us-west"
        ssd: "true"
    - uri: "qemu+ssh://host2.example.com/system"
      name: "host2"
      labels:
        region: "us-east"
        ssd: "false"
```

### 3. Systemd Service

**Use case**: Direct installation on Linux hosts

#### Service File

```ini
# /etc/systemd/system/hawkfish.service
[Unit]
Description=HawkFish Virtualization Controller
After=network.target libvirtd.service
Wants=libvirtd.service

[Service]
Type=exec
User=hawkfish
Group=hawkfish
WorkingDirectory=/opt/hawkfish
ExecStart=/opt/hawkfish/venv/bin/python -m hawkfish_controller
Environment=HF_STATE_DIR=/var/lib/hawkfish
Environment=HF_AUTH=sessions
Environment=HF_UI_ENABLED=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

#### Installation

```bash
# Create user
sudo useradd -r -s /bin/false hawkfish
sudo usermod -a -G libvirt hawkfish

# Install application
sudo mkdir -p /opt/hawkfish
sudo python -m venv /opt/hawkfish/venv
sudo /opt/hawkfish/venv/bin/pip install hawkfish-controller

# Create state directory
sudo mkdir -p /var/lib/hawkfish
sudo chown hawkfish:hawkfish /var/lib/hawkfish

# Install and start service
sudo systemctl enable hawkfish.service
sudo systemctl start hawkfish.service
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HF_API_HOST` | `0.0.0.0` | API bind address |
| `HF_API_PORT` | `8080` | API port |
| `HF_AUTH` | `none` | Authentication mode (`none`, `sessions`) |
| `HF_UI_ENABLED` | `false` | Enable web UI |
| `LIBVIRT_URI` | `qemu:///system` | Libvirt connection URI |
| `HF_STATE_DIR` | `/var/lib/hawkfish` | State directory |
| `HF_ISO_DIR` | `/var/lib/hawkfish/isos` | ISO storage directory |
| `HF_DEV_TLS` | `off` | TLS mode (`off`, `self-signed`, `custom`) |

### TLS Configuration

#### Self-Signed Certificates

```bash
export HF_DEV_TLS=self-signed
export HF_API_PORT=8443
python -m hawkfish_controller
```

#### Custom Certificates

```bash
export HF_DEV_TLS=custom
export HF_TLS_CERT=/path/to/server.crt
export HF_TLS_KEY=/path/to/server.key
python -m hawkfish_controller
```

#### Let's Encrypt (with Nginx)

```nginx
# /etc/nginx/sites-available/hawkfish
server {
    listen 443 ssl http2;
    server_name hawkfish.example.com;
    
    ssl_certificate /etc/letsencrypt/live/hawkfish.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/hawkfish.example.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # SSE support
    location /redfish/v1/EventService/Events {
        proxy_pass http://localhost:8080;
        proxy_set_header Connection '';
        proxy_http_version 1.1;
        chunked_transfer_encoding off;
        proxy_buffering off;
        proxy_cache off;
    }
}
```

### Database Configuration

HawkFish uses SQLite by default. For production deployments, consider:

#### Backup Strategy

```bash
# Automated backup
#!/bin/bash
backup_dir="/var/backups/hawkfish"
mkdir -p "$backup_dir"

hawkfish admin backup "$backup_dir/hawkfish-$(date +%Y%m%d-%H%M%S).tar.gz"

# Keep last 7 days
find "$backup_dir" -name "hawkfish-*.tar.gz" -mtime +7 -delete
```

#### Migration Planning

```bash
# Before upgrade
hawkfish admin backup pre-upgrade-backup.tar.gz

# After upgrade (if needed)
hawkfish admin restore pre-upgrade-backup.tar.gz --force
```

## Networking

### Libvirt Networking

#### Local Setup

```bash
# Default NAT network
virsh net-start default
virsh net-autostart default
```

#### Bridge Network

```bash
# Create bridge
sudo ip link add br0 type bridge
sudo ip link set br0 up

# Configure libvirt network
cat > bridge-network.xml << EOF
<network>
  <name>bridge</name>
  <forward mode="bridge"/>
  <bridge name="br0"/>
</network>
EOF

virsh net-define bridge-network.xml
virsh net-start bridge
virsh net-autostart bridge
```

#### Multi-Host SSH Access

```bash
# Generate SSH key for hawkfish user
sudo -u hawkfish ssh-keygen -t rsa -b 4096 -f /home/hawkfish/.ssh/id_rsa

# Copy to hypervisor hosts
sudo -u hawkfish ssh-copy-id user@hypervisor1.example.com
sudo -u hawkfish ssh-copy-id user@hypervisor2.example.com

# Test connectivity
sudo -u hawkfish virsh -c qemu+ssh://user@hypervisor1.example.com/system list
```

### Firewall Configuration

```bash
# UFW rules
sudo ufw allow 8080/tcp comment "HawkFish API"
sudo ufw allow 8443/tcp comment "HawkFish HTTPS"

# iptables rules
sudo iptables -A INPUT -p tcp --dport 8080 -j ACCEPT
sudo iptables -A INPUT -p tcp --dport 8443 -j ACCEPT
```

## Security

### Authentication

#### Session-based Authentication

```bash
# Enable sessions
export HF_AUTH=sessions

# Create user via API
curl -X POST http://localhost:8080/redfish/v1/AccountService/Accounts \
  -H "Content-Type: application/json" \
  -d '{"UserName": "admin", "Password": "secure-password", "RoleId": "Administrator"}'
```

#### API Keys (Future)

```bash
# Generate API key
hawkfish admin create-api-key --user admin --role Administrator --expires 90d
```

### Access Control

#### RBAC Configuration

```yaml
# User roles
users:
  - username: "admin"
    role: "Administrator"
    permissions: ["*"]
  - username: "operator"
    role: "Operator"
    permissions: ["systems:read", "systems:power", "media:*"]
  - username: "viewer"
    role: "ReadOnly"
    permissions: ["*:read"]
```

#### Network Isolation

```bash
# Restrict to management network
export HF_API_HOST=10.0.1.100

# Use SSH tunneling for remote access
ssh -L 8080:localhost:8080 user@hypervisor.example.com
```

### Secrets Management

#### Docker Secrets

```yaml
services:
  hawkfish:
    secrets:
      - hawkfish-admin-password
      - hawkfish-tls-cert
      - hawkfish-tls-key
    environment:
      HF_ADMIN_PASSWORD_FILE: /run/secrets/hawkfish-admin-password

secrets:
  hawkfish-admin-password:
    external: true
  hawkfish-tls-cert:
    file: ./certs/server.crt
  hawkfish-tls-key:
    file: ./certs/server.key
```

#### Kubernetes Secrets

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: hawkfish-tls
type: kubernetes.io/tls
data:
  tls.crt: <base64-encoded-cert>
  tls.key: <base64-encoded-key>
```

## Monitoring

### Health Checks

```bash
# API health
curl -f http://localhost:8080/redfish/v1/

# Container health
docker-compose ps
docker inspect hawkfish_hawkfish_1 --format='{{.State.Health.Status}}'
```

### Metrics

#### Prometheus Integration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'hawkfish'
    static_configs:
      - targets: ['hawkfish:8080']
    metrics_path: '/redfish/v1/metrics'
```

#### Key Metrics

- `hawkfish_api_requests_total`: Total API requests
- `hawkfish_api_request_duration_seconds`: Request latency
- `hawkfish_libvirt_pool_size`: Connection pool size
- `hawkfish_systems_total`: Total managed systems
- `hawkfish_events_delivered_total`: Event delivery count

### Logging

#### Structured Logging

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "INFO",
  "logger": "hawkfish.api.systems",
  "message": "System power action",
  "system_id": "vm-001",
  "action": "On",
  "user_id": "admin",
  "request_id": "req-123"
}
```

#### Log Aggregation

```yaml
# ELK Stack example
version: '3.8'
services:
  hawkfish:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
  
  filebeat:
    image: elastic/filebeat:8.0.0
    volumes:
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - ./filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
```

## Troubleshooting

### Common Issues

#### Connection Problems

```bash
# Test libvirt connectivity
virsh -c $LIBVIRT_URI list

# Check SSH access
ssh user@hypervisor.example.com virsh list

# Verify permissions
groups hawkfish  # Should include 'libvirt'
```

#### Performance Issues

```bash
# Check connection pool metrics
curl http://localhost:8080/redfish/v1/libvirt-pool-metrics

# Monitor resource usage
docker stats hawkfish_hawkfish_1
```

#### SSL/TLS Issues

```bash
# Test TLS connection
openssl s_client -connect localhost:8443 -servername localhost

# Verify certificate
openssl x509 -in /path/to/cert.crt -text -noout
```

### Debugging

#### Enable Debug Logging

```bash
export HAWKFISH_LOG_LEVEL=DEBUG
python -m hawkfish_controller
```

#### Container Debugging

```bash
# Access container shell
docker-compose exec hawkfish /bin/bash

# View container logs
docker-compose logs -f hawkfish

# Check container health
docker-compose ps
```

#### API Debugging

```bash
# Test API endpoints
curl -v http://localhost:8080/redfish/v1/

# Check auth
curl -H "X-Auth-Token: $TOKEN" http://localhost:8080/redfish/v1/Systems
```

## Scaling

### Horizontal Scaling

```yaml
# Multiple controller instances
services:
  hawkfish-1:
    image: hawkfish/hawkfish-controller:latest
    environment:
      HF_NODE_ID: "controller-1"
  
  hawkfish-2:
    image: hawkfish/hawkfish-controller:latest
    environment:
      HF_NODE_ID: "controller-2"
  
  nginx:
    image: nginx:alpine
    ports:
      - "8080:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

### Database Scaling

```bash
# Consider external database for multiple instances
export HF_DATABASE_URL="postgresql://user:pass@db:5432/hawkfish"
```

### Load Balancing

```nginx
upstream hawkfish_backend {
    server hawkfish-1:8080;
    server hawkfish-2:8080;
}

server {
    location / {
        proxy_pass http://hawkfish_backend;
    }
}
```
