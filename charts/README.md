# HawkFish Helm Charts

This directory contains Helm charts for deploying HawkFish on Kubernetes clusters.

## Available Charts

### hawkfish

The main HawkFish controller chart that provides:

- **HawkFish Controller**: The core API server and management interface
- **Storage Management**: Persistent volume claims for state and data
- **Security**: RBAC, network policies, and pod security contexts
- **Monitoring**: ServiceMonitor for Prometheus integration
- **Autoscaling**: Horizontal and Vertical Pod Autoscalers
- **High Availability**: Pod disruption budgets and anti-affinity rules

## Quick Start

### Prerequisites

- Kubernetes 1.21+
- Helm 3.8+
- StorageClass for persistent volumes (recommended)

### Installation

1. **Add the Helm repository** (when published):
   ```bash
   helm repo add hawkfish https://your-org.github.io/HawkFish/
   helm repo update
   ```

2. **Install from repository**:
   ```bash
   helm install hawkfish hawkfish/hawkfish --namespace hawkfish --create-namespace
   ```

3. **Install from local charts**:
   ```bash
   # From repository root
   helm install hawkfish ./charts/hawkfish --namespace hawkfish --create-namespace
   ```

### Configuration

The chart can be configured via values.yaml or command-line parameters:

```bash
# Basic configuration
helm install hawkfish ./charts/hawkfish \
  --namespace hawkfish --create-namespace \
  --set image.tag=0.1.0 \
  --set hawkfish.auth.enabled=true \
  --set persistence.enabled=true \
  --set persistence.size=10Gi
```

## Chart Development

### Directory Structure

```
charts/
├── README.md                    # This file
└── hawkfish/                   # Main HawkFish chart
    ├── Chart.yaml              # Chart metadata
    ├── values.yaml             # Default configuration values
    ├── templates/              # Kubernetes manifest templates
    │   ├── _helpers.tpl        # Template helpers
    │   ├── configmap.yaml      # Configuration management
    │   ├── deployment.yaml     # Main application deployment
    │   ├── service.yaml        # Service definition
    │   ├── serviceaccount.yaml # RBAC service account
    │   ├── ingress.yaml        # Ingress configuration
    │   ├── pvc.yaml           # Persistent volume claims
    │   ├── hpa.yaml           # Horizontal Pod Autoscaler
    │   ├── vpa.yaml           # Vertical Pod Autoscaler
    │   ├── pdb.yaml           # Pod Disruption Budget
    │   ├── networkpolicy.yaml # Network security policies
    │   ├── servicemonitor.yaml # Prometheus monitoring
    │   └── tests/             # Helm tests
    │       └── test-connection.yaml
    └── crds/                  # Custom Resource Definitions (if any)
```

### Development Workflow

1. **Lint charts**:
   ```bash
   make helm-lint
   ```

2. **Test templates**:
   ```bash
   make helm-template
   ```

3. **Update dependencies**:
   ```bash
   make helm-deps
   ```

4. **Package charts**:
   ```bash
   make helm-package
   ```

5. **Test locally**:
   ```bash
   make chart-install-local
   make chart-test
   make chart-uninstall-local
   ```

### Version Management

Chart versions are automatically managed:

- **Development**: Use `make chart-version-update` to sync with project version
- **Release**: GitHub Actions automatically updates versions on release tags
- **Manual**: Edit `Chart.yaml` directly if needed

### Testing

The chart includes comprehensive testing:

- **Lint Testing**: Validates chart syntax and best practices
- **Template Testing**: Ensures templates render correctly
- **Integration Testing**: Tests actual deployment on Kind clusters
- **Security Scanning**: Validates security configurations with Checkov

### Configuration Options

Key configuration sections in `values.yaml`:

```yaml
# Application image
image:
  repository: hawkfish/hawkfish-controller
  tag: "0.1.0"
  pullPolicy: IfNotPresent

# HawkFish-specific configuration
hawkfish:
  api:
    host: "0.0.0.0"
    port: 8000
  auth:
    enabled: true
    secret_key: ""  # Auto-generated if empty
  tls:
    enabled: false
    cert_file: ""
    key_file: ""

# Persistence
persistence:
  enabled: true
  storageClass: ""
  size: 5Gi
  accessMode: ReadWriteOnce

# Monitoring
metrics:
  enabled: true
  serviceMonitor:
    enabled: false

# Autoscaling
autoscaling:
  enabled: false
  minReplicas: 1
  maxReplicas: 10
  targetCPUUtilizationPercentage: 80

# Security
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000

securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 1000
  capabilities:
    drop:
    - ALL
```

## Publishing Charts

Charts are automatically published through GitHub Actions:

1. **On Pull Request**: Lint and test charts
2. **On Release**: Package and publish to GitHub Releases and OCI registry
3. **GitHub Pages**: Maintain Helm repository index

### Manual Publishing

```bash
# Package charts
make helm-package

# Push to OCI registry
helm push packaged-charts/hawkfish-*.tgz oci://ghcr.io/your-org/charts

# Update Helm repository (if using GitHub Pages)
helm repo index packaged-charts --url https://your-org.github.io/HawkFish/
```

## Troubleshooting

### Common Issues

1. **Persistent Volume Issues**:
   ```bash
   kubectl get pvc -n hawkfish
   kubectl describe pvc hawkfish-data -n hawkfish
   ```

2. **Pod Startup Issues**:
   ```bash
   kubectl logs -f deployment/hawkfish -n hawkfish
   kubectl describe pod -l app.kubernetes.io/name=hawkfish -n hawkfish
   ```

3. **Service Discovery**:
   ```bash
   kubectl get svc -n hawkfish
   kubectl get endpoints -n hawkfish
   ```

4. **Configuration Issues**:
   ```bash
   kubectl get configmap hawkfish-config -n hawkfish -o yaml
   ```

### Debug Mode

Enable debug mode for troubleshooting:

```bash
helm install hawkfish ./charts/hawkfish \
  --namespace hawkfish --create-namespace \
  --set hawkfish.debug=true \
  --set hawkfish.log_level=DEBUG
```

## Contributing

When contributing to charts:

1. Follow [Helm best practices](https://helm.sh/docs/chart_best_practices/)
2. Update chart version in `Chart.yaml`
3. Document changes in chart `CHANGELOG.md`
4. Test thoroughly with `make chart-test`
5. Ensure security compliance with `make helm-security-scan`

## Support

- **Documentation**: [docs/kubernetes.md](../docs/kubernetes.md)
- **Issues**: [GitHub Issues](https://github.com/your-org/HawkFish/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/HawkFish/discussions)
