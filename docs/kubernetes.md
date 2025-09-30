# Kubernetes Deployment Guide

This guide covers deploying HawkFish on Kubernetes using Helm charts, including production-ready configurations, scaling, and operational considerations.

## Overview

HawkFish provides comprehensive Kubernetes support through:
- **Helm Charts** - Production-ready deployment templates
- **Multi-architecture Images** - Support for AMD64 and ARM64
- **Cloud-Native Features** - Health checks, metrics, autoscaling
- **Security Best Practices** - Non-root containers, security contexts
- **Observability** - Prometheus metrics, structured logging

## Prerequisites

### Kubernetes Cluster Requirements
- **Kubernetes Version**: 1.20.0 or higher
- **Helm Version**: 3.8.0 or higher
- **Storage**: Dynamic volume provisioning (recommended)
- **Networking**: Ingress controller (for external access)

### Resource Requirements

#### Minimum (Development)
- **CPU**: 500m
- **Memory**: 1Gi
- **Storage**: 10Gi (data) + 50Gi (ISOs)

#### Recommended (Production)
- **CPU**: 2000m
- **Memory**: 4Gi
- **Storage**: 100Gi (data) + 200Gi (ISOs)
- **Replicas**: 2+ (with HPA)

## Installation

### Quick Start

```bash
# Add HawkFish Helm repository
helm repo add hawkfish https://charts.hawkfish.local
helm repo update

# Install with default values
helm install hawkfish hawkfish/hawkfish

# Check deployment status
kubectl get pods -l app.kubernetes.io/name=hawkfish
```

### Production Installation

```bash
# Create namespace
kubectl create namespace hawkfish

# Install with production values
helm install hawkfish hawkfish/hawkfish \
  --namespace hawkfish \
  --values production-values.yaml \
  --wait --timeout 10m
```

#### Production Values Example

```yaml
# production-values.yaml
replicaCount: 2

image:
  tag: "0.1.0"
  pullPolicy: IfNotPresent

resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 500m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

persistence:
  enabled: true
  storageClass: "fast-ssd"
  size: 100Gi
  
  isos:
    enabled: true
    storageClass: "standard"
    size: 200Gi
    accessMode: ReadWriteMany

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
  hosts:
    - host: hawkfish.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: hawkfish-tls
      hosts:
        - hawkfish.example.com

hawkfish:
  auth:
    enabled: true
    method: "sessions"
  
  database:
    type: "postgresql"
  
  multiTenant:
    enabled: true
  
  metrics:
    enabled: true

serviceMonitor:
  enabled: true
  labels:
    prometheus: kube-prometheus

postgresql:
  enabled: true
  auth:
    database: "hawkfish"
    username: "hawkfish"
    password: "secure-password"
  primary:
    persistence:
      enabled: true
      size: 20Gi

podDisruptionBudget:
  enabled: true
  minAvailable: 1
```

## Configuration

### Core Configuration

#### Application Settings
```yaml
hawkfish:
  # Core settings
  host: "0.0.0.0"
  port: 8080
  logLevel: "INFO"
  workerCount: 4
  
  # Authentication
  auth:
    enabled: true
    method: "sessions"  # sessions, oauth, ldap
    sessionTimeout: "24h"
  
  # Database
  database:
    type: "sqlite"  # sqlite, postgresql
    path: "/var/lib/hawkfish/data/hawkfish.db"
  
  # Multi-tenancy
  multiTenant:
    enabled: true
    defaultProject: "default"
```

#### Storage Configuration
```yaml
persistence:
  # Main data storage
  enabled: true
  storageClass: "fast-ssd"
  accessMode: ReadWriteOnce
  size: 100Gi
  
  # ISO image storage
  isos:
    enabled: true
    storageClass: "standard"
    accessMode: ReadWriteMany  # Required for multi-replica deployments
    size: 200Gi
```

#### Security Configuration
```yaml
podSecurityContext:
  fsGroup: 1000
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000

securityContext:
  allowPrivilegeEscalation: false
  capabilities:
    drop:
    - ALL
  readOnlyRootFilesystem: false
  runAsNonRoot: true
  runAsUser: 1000

networkPolicy:
  enabled: true
  ingress:
    - from:
      - namespaceSelector:
          matchLabels:
            name: monitoring
      ports:
      - protocol: TCP
        port: 8080
```

### External Dependencies

#### PostgreSQL Database
```yaml
postgresql:
  enabled: true
  auth:
    postgresPassword: "admin-password"
    username: "hawkfish"
    password: "hawkfish-password"
    database: "hawkfish"
  primary:
    persistence:
      enabled: true
      size: 20Gi
      storageClass: "fast-ssd"
```

#### Redis Cache (Optional)
```yaml
redis:
  enabled: true
  auth:
    enabled: true
    password: "redis-password"
  master:
    persistence:
      enabled: true
      size: 8Gi
```

## Scaling and High Availability

### Horizontal Pod Autoscaler

```yaml
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

### Vertical Pod Autoscaler

```yaml
verticalPodAutoscaler:
  enabled: true
  updateMode: "Auto"  # Off, Initial, Recreation, Auto
```

### Pod Disruption Budget

```yaml
podDisruptionBudget:
  enabled: true
  minAvailable: 1
  # maxUnavailable: 50%
```

### Affinity and Anti-Affinity

```yaml
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        labelSelector:
          matchExpressions:
          - key: app.kubernetes.io/name
            operator: In
            values:
            - hawkfish
        topologyKey: kubernetes.io/hostname
```

## Monitoring and Observability

### Prometheus Integration

```yaml
serviceMonitor:
  enabled: true
  namespace: "monitoring"
  labels:
    prometheus: kube-prometheus
  interval: 30s
  scrapeTimeout: 10s
  path: /redfish/v1/metrics
```

### Grafana Dashboard

HawkFish provides a pre-built Grafana dashboard for monitoring:

```bash
# Import dashboard from ConfigMap
kubectl apply -f - <<EOF
apiVersion: v1
kind: ConfigMap
metadata:
  name: hawkfish-dashboard
  namespace: monitoring
  labels:
    grafana_dashboard: "1"
data:
  hawkfish.json: |
    {
      "dashboard": {
        "title": "HawkFish Metrics",
        "panels": [
          {
            "title": "API Requests",
            "type": "graph",
            "targets": [
              {
                "expr": "rate(hawkfish_http_requests_total[5m])"
              }
            ]
          }
        ]
      }
    }
EOF
```

### Logging

Configure structured logging for Kubernetes:

```yaml
hawkfish:
  logLevel: "INFO"
  extraEnvVars:
    - name: HF_LOG_FORMAT
      value: "json"
    - name: HF_LOG_STRUCTURED
      value: "true"
```

## Networking

### Ingress Configuration

#### NGINX Ingress
```yaml
ingress:
  enabled: true
  className: "nginx"
  annotations:
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
  hosts:
    - host: hawkfish.example.com
      paths:
        - path: /
          pathType: Prefix
```

#### Traefik Ingress
```yaml
ingress:
  enabled: true
  className: "traefik"
  annotations:
    traefik.ingress.kubernetes.io/router.middlewares: "default-auth@kubernetescrd"
  hosts:
    - host: hawkfish.example.com
      paths:
        - path: /
          pathType: Prefix
```

### Service Configuration

```yaml
service:
  type: ClusterIP  # ClusterIP, NodePort, LoadBalancer
  port: 80
  targetPort: 8080
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"  # AWS
```

### Network Policies

```yaml
networkPolicy:
  enabled: true
  ingress:
    # Allow ingress controller
    - from:
      - namespaceSelector:
          matchLabels:
            name: ingress-nginx
      ports:
      - protocol: TCP
        port: 8080
    
    # Allow monitoring
    - from:
      - namespaceSelector:
          matchLabels:
            name: monitoring
      ports:
      - protocol: TCP
        port: 8080
  
  egress:
    # Allow DNS
    - to: []
      ports:
      - protocol: UDP
        port: 53
    
    # Allow PostgreSQL
    - to:
      - podSelector:
          matchLabels:
            app.kubernetes.io/name: postgresql
      ports:
      - protocol: TCP
        port: 5432
```

## Security

### RBAC Configuration

```yaml
serviceAccount:
  create: true
  annotations:
    eks.amazonaws.com/role-arn: "arn:aws:iam::ACCOUNT:role/hawkfish-role"  # AWS
  name: "hawkfish"
  automountServiceAccountToken: true
```

### Secrets Management

```bash
# Create database secret
kubectl create secret generic hawkfish-db \
  --from-literal=database-url="postgresql://user:pass@host:5432/hawkfish"

# Create TLS secret
kubectl create secret tls hawkfish-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key
```

### Pod Security Standards

```yaml
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault

securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: false
  runAsNonRoot: true
  runAsUser: 1000
  capabilities:
    drop:
    - ALL
```

## Backup and Recovery

### Database Backup

```bash
# PostgreSQL backup
kubectl exec -it postgresql-0 -- pg_dump -U hawkfish hawkfish > hawkfish-backup.sql

# Restore
kubectl exec -i postgresql-0 -- psql -U hawkfish hawkfish < hawkfish-backup.sql
```

### Persistent Volume Backup

```yaml
# VolumeSnapshot (if supported)
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: hawkfish-data-snapshot
spec:
  volumeSnapshotClassName: csi-snapclass
  source:
    persistentVolumeClaimName: hawkfish-data
```

## Troubleshooting

### Common Issues

#### Pod Startup Issues
```bash
# Check pod status
kubectl get pods -l app.kubernetes.io/name=hawkfish

# Check logs
kubectl logs -l app.kubernetes.io/name=hawkfish --tail=100

# Describe pod for events
kubectl describe pod <pod-name>
```

#### Storage Issues
```bash
# Check PVC status
kubectl get pvc

# Check storage class
kubectl get storageclass

# Check volume mounts
kubectl exec -it <pod-name> -- df -h
```

#### Network Issues
```bash
# Test service connectivity
kubectl run test-pod --image=curlimages/curl -it --rm -- /bin/sh
curl http://hawkfish:80/redfish/v1/

# Check ingress
kubectl get ingress
kubectl describe ingress hawkfish
```

### Debug Mode

Enable debug logging:

```yaml
hawkfish:
  logLevel: "DEBUG"
  extraEnvVars:
    - name: HF_DEBUG
      value: "true"
```

### Health Checks

```bash
# Check readiness
kubectl exec <pod-name> -- curl -f http://localhost:8080/redfish/v1/

# Check liveness
kubectl exec <pod-name> -- curl -f http://localhost:8080/redfish/v1/
```

## Upgrading

### Helm Upgrade

```bash
# Update repository
helm repo update

# Upgrade release
helm upgrade hawkfish hawkfish/hawkfish \
  --namespace hawkfish \
  --values production-values.yaml \
  --wait --timeout 10m

# Check upgrade status
helm status hawkfish -n hawkfish
```

### Rolling Updates

```yaml
# Configure rolling update strategy
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
```

### Database Migrations

```bash
# Run database migrations (if needed)
kubectl exec -it <pod-name> -- python -m hawkfish_controller migrate
```

## Performance Optimization

### Resource Tuning

```yaml
resources:
  limits:
    cpu: 4000m
    memory: 8Gi
  requests:
    cpu: 1000m
    memory: 2Gi

hawkfish:
  workerCount: 8  # Adjust based on CPU cores
```

### Storage Optimization

```yaml
persistence:
  storageClass: "fast-ssd"  # Use fast storage
  
  isos:
    storageClass: "standard"  # Use cheaper storage for ISOs
```

### Network Optimization

```yaml
service:
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: "tcp"
    service.beta.kubernetes.io/aws-load-balancer-connection-idle-timeout: "300"
```

## Multi-Cluster Deployment

### Cluster Federation

```yaml
# Deploy to multiple clusters
helm install hawkfish-us-west hawkfish/hawkfish \
  --set hawkfish.region=us-west

helm install hawkfish-us-east hawkfish/hawkfish \
  --set hawkfish.region=us-east
```

### Cross-Cluster Networking

```yaml
hawkfish:
  hosts:
    - uri: "qemu+ssh://cluster-b-host/system"
      name: "cluster-b-host"
      labels:
        region: "us-east"
        cluster: "production-east"
```

## Best Practices

### Production Checklist

- [ ] Use specific image tags (not `latest`)
- [ ] Configure resource limits and requests
- [ ] Enable persistence with appropriate storage classes
- [ ] Set up monitoring and alerting
- [ ] Configure backup strategies
- [ ] Implement network policies
- [ ] Use non-root security contexts
- [ ] Configure pod disruption budgets
- [ ] Set up horizontal pod autoscaling
- [ ] Configure ingress with TLS
- [ ] Use secrets for sensitive data
- [ ] Enable audit logging
- [ ] Test disaster recovery procedures

### Security Hardening

- Use Pod Security Standards
- Implement network segmentation
- Regular security scanning
- Principle of least privilege
- Encrypted storage
- Secure secret management
- Regular updates and patches

### Monitoring Strategy

- Application metrics (Prometheus)
- Infrastructure metrics (Node Exporter)
- Log aggregation (ELK/Loki)
- Distributed tracing (Jaeger)
- Alerting rules (AlertManager)
- SLA/SLO monitoring

For more information, see the [Operations Guide](ops.md) and [Performance Tuning](scale-performance.md) documentation.
