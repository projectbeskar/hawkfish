# Kubernetes Examples

This directory contains comprehensive examples for deploying and managing HawkFish on Kubernetes.

## Quick Start

### Basic Deployment

```bash
# Install HawkFish with default settings
helm repo add hawkfish https://charts.hawkfish.local
helm install hawkfish hawkfish/hawkfish
```

### Production Deployment

```bash
# Deploy with production configuration
helm install hawkfish hawkfish/hawkfish \
  --values examples/kubernetes/production-values.yaml \
  --namespace hawkfish \
  --create-namespace
```

## Examples Overview

### Deployment Configurations
- [`basic-values.yaml`](basic-values.yaml) - Minimal development setup
- [`production-values.yaml`](production-values.yaml) - Production-ready configuration
- [`high-availability.yaml`](high-availability.yaml) - Multi-replica HA setup
- [`multi-tenant.yaml`](multi-tenant.yaml) - Multi-tenancy configuration

### Infrastructure Examples
- [`ingress-nginx.yaml`](ingress-nginx.yaml) - NGINX Ingress configuration
- [`ingress-traefik.yaml`](ingress-traefik.yaml) - Traefik Ingress configuration
- [`monitoring.yaml`](monitoring.yaml) - Prometheus and Grafana setup
- [`network-policies.yaml`](network-policies.yaml) - Network security policies

### Storage Examples
- [`storage-local.yaml`](storage-local.yaml) - Local storage configuration
- [`storage-nfs.yaml`](storage-nfs.yaml) - NFS storage setup
- [`storage-ceph.yaml`](storage-ceph.yaml) - Ceph RBD configuration
- [`backup-cronjob.yaml`](backup-cronjob.yaml) - Automated backup job

### Security Examples
- [`rbac.yaml`](rbac.yaml) - Role-based access control
- [`pod-security.yaml`](pod-security.yaml) - Pod security policies
- [`secrets.yaml`](secrets.yaml) - Secret management examples
- [`tls-config.yaml`](tls-config.yaml) - TLS certificate configuration

### Scaling Examples
- [`hpa.yaml`](hpa.yaml) - Horizontal Pod Autoscaler
- [`vpa.yaml`](vpa.yaml) - Vertical Pod Autoscaler
- [`cluster-autoscaler.yaml`](cluster-autoscaler.yaml) - Cluster scaling configuration

## Getting Started

### Prerequisites

1. **Kubernetes Cluster** (1.20+)
   ```bash
   kubectl version --short
   ```

2. **Helm** (3.8+)
   ```bash
   helm version --short
   ```

3. **Storage Class** (for persistence)
   ```bash
   kubectl get storageclass
   ```

### Installation Steps

1. **Add Helm Repository**
   ```bash
   helm repo add hawkfish https://charts.hawkfish.local
   helm repo update
   ```

2. **Create Namespace**
   ```bash
   kubectl create namespace hawkfish
   ```

3. **Install HawkFish**
   ```bash
   # Basic installation
   helm install hawkfish hawkfish/hawkfish -n hawkfish
   
   # With custom values
   helm install hawkfish hawkfish/hawkfish \
     -n hawkfish \
     -f examples/kubernetes/production-values.yaml
   ```

4. **Verify Installation**
   ```bash
   kubectl get pods -n hawkfish
   kubectl get svc -n hawkfish
   ```

### Access HawkFish

#### Port Forward (Development)
```bash
kubectl port-forward -n hawkfish svc/hawkfish 8080:80
curl http://localhost:8080/redfish/v1/
```

#### Ingress (Production)
```bash
# Apply ingress configuration
kubectl apply -f examples/kubernetes/ingress-nginx.yaml

# Access via domain
curl https://hawkfish.example.com/redfish/v1/
```

## Configuration Examples

### Development Setup

Minimal configuration for development and testing:

```yaml
# dev-values.yaml
replicaCount: 1

resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 1Gi

persistence:
  enabled: true
  size: 5Gi

hawkfish:
  logLevel: "DEBUG"
  auth:
    enabled: false
```

### Production Setup

Production-ready configuration with HA and monitoring:

```yaml
# production-values.yaml
replicaCount: 3

image:
  tag: "0.1.0"
  pullPolicy: IfNotPresent

resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 4Gi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

persistence:
  enabled: true
  storageClass: "fast-ssd"
  size: 100Gi
  
  isos:
    enabled: true
    storageClass: "standard"
    size: 200Gi

ingress:
  enabled: true
  className: "nginx"
  hosts:
    - host: hawkfish.example.com
      paths:
        - path: /
          pathType: Prefix

hawkfish:
  auth:
    enabled: true
    method: "sessions"
  
  database:
    type: "postgresql"
  
  multiTenant:
    enabled: true

postgresql:
  enabled: true
  auth:
    database: "hawkfish"
    username: "hawkfish"
    password: "secure-password"

serviceMonitor:
  enabled: true
```

## Monitoring Setup

### Prometheus and Grafana

1. **Install Prometheus Operator**
   ```bash
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm install prometheus prometheus-community/kube-prometheus-stack \
     -n monitoring --create-namespace
   ```

2. **Enable ServiceMonitor**
   ```yaml
   serviceMonitor:
     enabled: true
     labels:
       prometheus: kube-prometheus
   ```

3. **Import Grafana Dashboard**
   ```bash
   kubectl apply -f examples/kubernetes/monitoring.yaml
   ```

### Log Aggregation

#### ELK Stack
```bash
# Install Elasticsearch and Kibana
helm repo add elastic https://helm.elastic.co
helm install elasticsearch elastic/elasticsearch -n logging --create-namespace
helm install kibana elastic/kibana -n logging
```

#### Loki Stack
```bash
# Install Loki and Grafana
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack -n logging --create-namespace
```

## Security Configuration

### Network Policies

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: hawkfish-netpol
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: hawkfish
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8080
```

### Pod Security

```yaml
# pod-security.yaml
apiVersion: v1
kind: Pod
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
  containers:
  - name: hawkfish
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: false
      capabilities:
        drop:
        - ALL
```

## Backup and Recovery

### Database Backup

```yaml
# backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: hawkfish-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:13
            command:
            - /bin/bash
            - -c
            - |
              pg_dump $DATABASE_URL > /backup/hawkfish-$(date +%Y%m%d).sql
              # Upload to S3 or other storage
            env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: hawkfish-db
                  key: database-url
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
          restartPolicy: OnFailure
```

### Volume Snapshots

```yaml
# volume-snapshot.yaml
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

#### Pod Not Starting
```bash
# Check pod status
kubectl get pods -n hawkfish

# Check events
kubectl describe pod <pod-name> -n hawkfish

# Check logs
kubectl logs <pod-name> -n hawkfish
```

#### Storage Issues
```bash
# Check PVC status
kubectl get pvc -n hawkfish

# Check storage class
kubectl get storageclass

# Check node storage
kubectl describe node <node-name>
```

#### Network Connectivity
```bash
# Test service connectivity
kubectl run test-pod --image=curlimages/curl -it --rm -- /bin/sh
curl http://hawkfish.hawkfish.svc.cluster.local/redfish/v1/

# Check ingress
kubectl get ingress -n hawkfish
kubectl describe ingress hawkfish -n hawkfish
```

### Debug Commands

```bash
# Get all resources
kubectl get all -n hawkfish

# Check resource usage
kubectl top pods -n hawkfish
kubectl top nodes

# Check cluster events
kubectl get events -n hawkfish --sort-by='.lastTimestamp'

# Debug networking
kubectl exec -it <pod-name> -n hawkfish -- netstat -tlnp
kubectl exec -it <pod-name> -n hawkfish -- nslookup kubernetes.default
```

## Upgrading

### Helm Upgrade

```bash
# Update repository
helm repo update

# Upgrade release
helm upgrade hawkfish hawkfish/hawkfish \
  -n hawkfish \
  -f production-values.yaml

# Check upgrade status
helm status hawkfish -n hawkfish
helm history hawkfish -n hawkfish
```

### Rollback

```bash
# Rollback to previous version
helm rollback hawkfish -n hawkfish

# Rollback to specific revision
helm rollback hawkfish 2 -n hawkfish
```

## Performance Optimization

### Resource Tuning

```yaml
resources:
  requests:
    cpu: 1000m      # Guaranteed CPU
    memory: 2Gi     # Guaranteed memory
  limits:
    cpu: 4000m      # Maximum CPU
    memory: 8Gi     # Maximum memory

hawkfish:
  workerCount: 8    # Match CPU cores
```

### Storage Performance

```yaml
persistence:
  storageClass: "fast-ssd"  # Use fast storage
  
  isos:
    storageClass: "standard"  # Use cheaper storage for ISOs
```

### Network Performance

```yaml
service:
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-backend-protocol: "tcp"
    service.beta.kubernetes.io/aws-load-balancer-connection-idle-timeout: "300"
```

## Best Practices

### Production Checklist

- [ ] Use specific image tags
- [ ] Configure resource limits
- [ ] Enable persistence
- [ ] Set up monitoring
- [ ] Configure backups
- [ ] Implement security policies
- [ ] Use ingress with TLS
- [ ] Configure autoscaling
- [ ] Set up network policies
- [ ] Test disaster recovery

### Security Best Practices

- Use non-root containers
- Implement network segmentation
- Regular security scanning
- Secure secret management
- Enable audit logging
- Use Pod Security Standards

### Monitoring Best Practices

- Monitor application metrics
- Set up alerting rules
- Implement log aggregation
- Use distributed tracing
- Monitor infrastructure health
- Define SLA/SLO metrics

For more detailed information, see the [Kubernetes Deployment Guide](../docs/kubernetes.md).
