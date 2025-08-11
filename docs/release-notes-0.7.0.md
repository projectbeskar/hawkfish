# HawkFish v0.7.0 Release Notes

**Release Date**: January 2024  
**Codename**: "Falcon" - Major UI, Packaging, SDKs, and Operations release

## 🎯 Major Features

### 🖥️ Web UI v1 (Preview)
- **React-based Dashboard**: Modern, responsive interface for VM management
- **Real-time Updates**: Live power states via Server-Sent Events (SSE)
- **System Management**: Power control, boot configuration, virtual media
- **Event Monitoring**: Live events panel with filtering and details
- **Mobile Responsive**: Works on desktop, tablet, and mobile devices

### 🔗 Libvirt Connection Pooling
- **Production-Ready Pooling**: Thread-safe connection management with health checks
- **Auto-Reconnection**: Resilient connections with exponential backoff
- **Performance Metrics**: Pool utilization and connection statistics
- **Configurable Limits**: Min/max connections and TTL settings

### 📦 Deployment & Packaging
- **Docker Container**: Multi-stage build with security hardening
- **Helm Chart**: Kubernetes deployment with full configuration support
- **Docker Compose**: Single-host development and production setup
- **CI/CD Integration**: Automated builds, SBOM generation, vulnerability scanning

### 🤖 SDKs & Automation
- **Python SDK**: Async client library with examples and error handling
- **Terraform Provider**: Infrastructure as Code for VM lifecycle management
- **Ansible Collection**: Playbooks and modules for configuration management
- **OpenAPI Specification**: Complete API documentation and code generation

### 🔧 Operations Hardening
- **Backup/Restore**: Complete state backup with CLI commands
- **Audit Logging**: Comprehensive audit trail for all operations
- **Performance Testing**: Load testing suite with latency targets
- **Security Enhancements**: Rate limiting, improved error handling

## 🚀 New Features

### User Interface
- **Login System**: Token-based authentication with session management
- **Systems Dashboard**: Tabular view with power states and quick actions
- **System Details**: Comprehensive drawer with power, boot, and media controls
- **Events Stream**: Real-time SSE events with expandable JSON payloads
- **Responsive Design**: Tailwind CSS with mobile-first approach

### API Enhancements
- **Collection Pagination**: Efficient pagination for all collection endpoints
- **Rate Limiting**: Token bucket rate limiting with 429 error responses
- **Audit Endpoints**: `/Oem/HawkFish/Audit/Logs` and `/Audit/Stats`
- **Pool Metrics**: `/libvirt-pool-metrics` for connection monitoring

### Infrastructure Features
- **Container Hardening**: Non-root user, read-only filesystem, dropped capabilities
- **Helm Configuration**: Complete values.yaml with all HawkFish options
- **Health Checks**: HTTP health checks and readiness probes
- **Secrets Management**: Support for Kubernetes secrets and Docker secrets

### Automation & SDKs
- **Python Client**: Full async API client with retry logic and error handling
- **Terraform Resources**: `hawkfish_system`, `hawkfish_profile`, `hawkfish_power`
- **Ansible Modules**: System lifecycle and power management modules
- **CI/CD Examples**: GitHub Actions, GitLab CI, Jenkins pipelines

### Operations & Monitoring
- **Backup Service**: SQLite backup with metadata preservation
- **Audit Logging**: Append-only audit trail with filtering and statistics
- **Performance Metrics**: Latency histograms and throughput counters
- **Load Testing**: Automated performance testing with configurable targets

## 🔧 Configuration Changes

### New Environment Variables
```bash
# UI Configuration
HF_UI_ENABLED=true              # Enable web UI serving

# Connection Pooling
HF_LIBVIRT_POOL_MIN=1           # Minimum pool connections
HF_LIBVIRT_POOL_MAX=10          # Maximum pool connections
HF_LIBVIRT_POOL_TTL_SEC=300     # Connection TTL in seconds
```

### Docker Environment
```yaml
services:
  hawkfish:
    image: hawkfish/hawkfish-controller:0.7.0
    environment:
      HF_UI_ENABLED: "true"
      HF_AUTH: "sessions"
      HF_LIBVIRT_POOL_MAX: "20"
```

### Helm Values
```yaml
hawkfish:
  ui:
    enabled: true
  libvirt:
    pool:
      min: 2
      max: 20
      ttlSec: 600
```

## 📈 Performance Improvements

### Connection Management
- **Pool Efficiency**: 3-5x reduction in connection overhead
- **Health Checking**: Proactive connection validation and replacement
- **Concurrent Operations**: Thread-safe libvirt access

### API Performance
- **Pagination**: Efficient large collection handling
- **Rate Limiting**: Protection against API abuse
- **Caching**: Connection pool caching and reuse

### Load Testing Results
| Endpoint | RPS | 95th Percentile |
|----------|-----|----------------|
| Service Root | 200+ | < 100ms |
| Systems List | 50+ | < 500ms |
| Power Actions | 20+ | < 1000ms |

## 🔐 Security Enhancements

### Rate Limiting
- **Token Bucket Algorithm**: Per-user rate limiting
- **Configurable Limits**: Default 100 req/min, burst 200
- **HTTP 429 Responses**: Proper rate limit error handling

### Container Security
- **Non-root Execution**: UID 1000 with dropped privileges
- **Read-only Filesystem**: Immutable container filesystem
- **Security Contexts**: Kubernetes security policies

### Audit Trail
- **Complete Logging**: All state changes logged with context
- **Retention Policies**: Configurable audit log retention
- **Admin Access**: Audit logs restricted to admin users

## 🐛 Bug Fixes

### Connection Stability
- **Pool Reconnection**: Automatic recovery from connection failures
- **Thread Safety**: Resolved concurrent access issues
- **Memory Leaks**: Fixed libvirt connection cleanup

### API Consistency
- **Error Responses**: Standardized Redfish error formats
- **Status Codes**: Correct HTTP status codes for all operations
- **Content Types**: Proper JSON content type headers

### UI Reliability
- **SSE Reconnection**: Automatic reconnection on connection drops
- **Error Handling**: Graceful handling of API errors
- **State Sync**: Consistent UI state with backend

## 📋 Migration Guide

### From v0.6.x to v0.7.0

1. **Backup Current State**:
   ```bash
   hawkfish admin backup pre-v0.7.0-backup.tar.gz
   ```

2. **Update Configuration**:
   ```bash
   # Enable new features
   export HF_UI_ENABLED=true
   export HF_LIBVIRT_POOL_MAX=10
   ```

3. **Upgrade Package**:
   ```bash
   pip install --upgrade hawkfish==0.7.0
   ```

4. **Verify Installation**:
   ```bash
   # Check API
   curl http://localhost:8080/redfish/v1/
   
   # Check UI (if enabled)
   curl http://localhost:8080/ui/
   ```

### Container Migration
```bash
# Update compose file
image: hawkfish/hawkfish-controller:0.7.0

# Pull new image
docker-compose pull
docker-compose up -d
```

### Kubernetes Migration
```bash
# Update Helm chart
helm upgrade hawkfish deploy/helm/ \
  --set image.tag=0.7.0 \
  --set hawkfish.ui.enabled=true
```

## 📚 Documentation Updates

### New Guides
- **[UI Documentation](ui.md)**: Complete web interface guide
- **[Deployment Guide](deploy.md)**: Docker, Kubernetes, and systemd deployment
- **[Automation Guide](automation.md)**: SDKs, Terraform, and Ansible integration
- **[Operations Guide](ops.md)**: Backup, monitoring, and maintenance procedures

### Updated Documentation
- **[Quickstart](quickstart.md)**: Updated with UI and container examples
- **[API Reference](api-reference.md)**: New endpoints and pagination
- **[Architecture](architecture.md)**: Connection pooling and UI components

## 🧪 Testing

### New Test Suites
- **Performance Tests**: Load testing with configurable targets
- **UI Tests**: Playwright end-to-end testing (planned)
- **Integration Tests**: Container and deployment testing

### Test Coverage
- **Unit Tests**: 85%+ coverage on core components
- **Integration Tests**: API and database testing
- **Performance Tests**: Latency and throughput validation

## 🚧 Known Issues

### UI Limitations (Preview)
- **Authentication**: Token-only authentication (no session cookies)
- **Mobile UX**: Some mobile interactions need refinement
- **Accessibility**: WCAG compliance improvements needed

### Container Considerations
- **Build Time**: Multi-stage build increases build duration
- **Image Size**: Larger image due to UI assets (~200MB)
- **Node.js Dependencies**: UI build requires Node.js 18+

### Performance Notes
- **SQLite Limitations**: Single-writer limitations for high concurrency
- **Connection Pool**: May need tuning for very high loads
- **Memory Usage**: Increased memory footprint with connection pooling

## 🔮 Looking Ahead: v0.8.0

### Planned Features
- **Multi-tenancy**: Namespace isolation and RBAC
- **PostgreSQL Support**: External database option for scaling
- **Advanced Networking**: VLAN and SR-IOV support
- **GPU Passthrough**: GPU resource management

### UI Improvements
- **Mobile App**: Native mobile application
- **Advanced Features**: Bulk operations, system templates
- **Accessibility**: Full WCAG 2.1 AA compliance

### Enterprise Features
- **LDAP Integration**: Enterprise authentication
- **High Availability**: Multi-instance deployment
- **Backup Scheduling**: Automated backup management

## 🙏 Acknowledgments

Thanks to all contributors who made v0.7.0 possible:
- UI/UX design and React implementation
- Container security and deployment improvements
- Performance testing and optimization
- Documentation and example contributions

## 📞 Support

- **Documentation**: [docs/](../docs/)
- **Issues**: [GitHub Issues](https://github.com/projectbeskar/hawkfish/issues)
- **Discussions**: [GitHub Discussions](https://github.com/projectbeskar/hawkfish/discussions)
- **Security**: security@projectbeskar.org

---

**Full Changelog**: [v0.6.0...v0.7.0](https://github.com/projectbeskar/hawkfish/compare/v0.6.0...v0.7.0)
