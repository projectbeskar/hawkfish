# Installation Requirements

This document outlines the system requirements and dependencies for running HawkFish.

## System Requirements

### Minimum Requirements
- **Operating System**: Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+, or equivalent)
- **CPU**: 2 cores (x86_64 or ARM64)
- **Memory**: 4 GB RAM
- **Storage**: 20 GB available disk space
- **Python**: Version 3.11 or higher

### Recommended Requirements
- **Operating System**: Ubuntu 22.04 LTS or RHEL 9
- **CPU**: 4+ cores with hardware virtualization support (Intel VT-x or AMD-V)
- **Memory**: 8+ GB RAM (more for running VMs)
- **Storage**: 100+ GB SSD storage
- **Network**: Gigabit Ethernet or faster

### For Production Use
- **CPU**: 8+ cores with virtualization extensions
- **Memory**: 16+ GB RAM (additional 2-4 GB per concurrent VM)
- **Storage**: Fast SSD storage (NVMe preferred)
- **Network**: Multiple network interfaces for VM isolation
- **High Availability**: Multiple hosts for live migration support

## Software Dependencies

### Core Dependencies
All core dependencies are automatically installed via pip:

```bash
# Install HawkFish with all dependencies
pip install hawkfish[virt]
```

#### Python Runtime Dependencies
- **FastAPI** (>=0.110.0) - Web framework and API server
- **Uvicorn** (>=0.27.0) - ASGI server with performance optimizations
- **Pydantic** (>=2.5.0) - Data validation and serialization
- **SQLite** - Database backend (included with Python)
- **Cryptography** (>=42.0.0) - TLS and security operations

#### Optional Dependencies
- **libvirt-python** (>=9.0.0) - KVM/libvirt integration (requires `[virt]` extra)

### Virtualization Stack (Optional)

For full functionality with VM management:

#### Ubuntu/Debian
```bash
# Install KVM and libvirt
sudo apt update
sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients

# Add user to libvirt group
sudo usermod -a -G libvirt $USER
newgrp libvirt

# Verify installation
virsh list --all
```

#### RHEL/CentOS/Fedora
```bash
# Install KVM and libvirt
sudo dnf install -y qemu-kvm libvirt libvirt-daemon-system virt-manager

# Start and enable libvirt
sudo systemctl start libvirtd
sudo systemctl enable libvirtd

# Add user to libvirt group
sudo usermod -a -G libvirt $USER
```

#### Verification
```bash
# Check hardware virtualization support
egrep -c '(vmx|svm)' /proc/cpuinfo

# Verify KVM modules
lsmod | grep kvm

# Test libvirt connection
virsh uri
virsh nodeinfo
```

### Container Runtime (Optional)

For Docker deployments:

#### Docker
```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# RHEL/Fedora
sudo dnf install -y docker
sudo systemctl start docker
sudo systemctl enable docker
```

#### Docker Compose
```bash
# Install Docker Compose v2
sudo apt install -y docker-compose-plugin
# or
pip install docker-compose
```

### Kubernetes (Optional)

For Kubernetes deployments:

#### kubectl
```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl
```

#### Helm
```bash
# Install Helm
curl https://baltocdn.com/charts/hawkfish/signing.asc | gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/charts/hawkfish/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
sudo apt update
sudo apt install helm
```

## Network Configuration

### Firewall Requirements
HawkFish requires the following ports to be accessible:

#### Controller Service
- **8080/tcp** - HTTP API (default, configurable)
- **8443/tcp** - HTTPS API (when TLS is enabled)

#### Libvirt (if used)
- **16509/tcp** - libvirt daemon (local connections)
- **16514/tcp** - libvirt TLS (remote connections)

#### VM Console Access
- **5900-5999/tcp** - VNC console range (configurable)
- **Dynamic** - WebSocket console proxy (ephemeral ports)

### Example Firewall Configuration

#### UFW (Ubuntu)
```bash
# Allow HawkFish API
sudo ufw allow 8080/tcp
sudo ufw allow 8443/tcp

# Allow libvirt (if using remote hosts)
sudo ufw allow 16509/tcp
sudo ufw allow 16514/tcp

# Allow VNC range for console access
sudo ufw allow 5900:5999/tcp
```

#### firewalld (RHEL/Fedora)
```bash
# Allow HawkFish API
sudo firewall-cmd --permanent --add-port=8080/tcp
sudo firewall-cmd --permanent --add-port=8443/tcp

# Allow libvirt
sudo firewall-cmd --permanent --add-service=libvirt
sudo firewall-cmd --permanent --add-service=libvirt-tls

# Reload configuration
sudo firewall-cmd --reload
```

## Storage Considerations

### Database Storage
- **SQLite files**: Stored in `~/.local/share/hawkfish/` by default
- **Recommended**: Place on fast SSD storage
- **Backup**: Regular database backups recommended for production

### VM Storage
- **Default location**: `/var/lib/libvirt/images/`
- **Requirements**: Fast storage for VM disk images
- **Formats**: qcow2 (default), raw, VMDK
- **Sizing**: Plan for VM disk space + snapshot overhead

### ISO Images
- **Storage location**: Configurable via `HF_ISO_PATH`
- **Network access**: HTTP/HTTPS URLs supported
- **Caching**: Images cached locally after first download

## Performance Tuning

### System Limits
```bash
# Increase file descriptor limits
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf
```

### KVM/QEMU Settings
```bash
# Enable KSM for memory optimization
echo 1 | sudo tee /sys/kernel/mm/ksm/run

# Optimize transparent hugepages
echo madvise | sudo tee /sys/kernel/mm/transparent_hugepage/enabled
```

### Network Performance
```bash
# Increase network buffer sizes
echo 'net.core.rmem_max = 134217728' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max = 134217728' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

## Validation

### Quick Validation Script
```bash
#!/bin/bash
# HawkFish requirements validation

echo "Checking HawkFish requirements..."

# Check Python version
python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
echo "Python version: $python_version"

# Check virtualization support
if grep -q 'vmx\|svm' /proc/cpuinfo; then
    echo "✓ Hardware virtualization supported"
else
    echo "⚠ Hardware virtualization not detected"
fi

# Check KVM
if lsmod | grep -q kvm; then
    echo "✓ KVM modules loaded"
else
    echo "⚠ KVM modules not loaded"
fi

# Check libvirt
if systemctl is-active --quiet libvirtd; then
    echo "✓ libvirtd service running"
else
    echo "⚠ libvirtd service not running"
fi

# Check libvirt connection
if virsh uri >/dev/null 2>&1; then
    echo "✓ libvirt connection available"
else
    echo "⚠ libvirt connection failed"
fi

# Check available memory
mem_gb=$(free -g | awk '/^Mem:/{print $2}')
echo "Available memory: ${mem_gb}GB"

# Check available disk space
disk_gb=$(df / | awk 'NR==2{print int($4/1024/1024)}')
echo "Available disk space: ${disk_gb}GB"

echo "Requirements check complete."
```

### Installation Test
```bash
# Test installation
python3 -m venv test-env
source test-env/bin/activate
pip install hawkfish[virt]

# Verify installation
hawkfish-controller --help
python -c "import hawkfish_controller; print('✓ HawkFish installed successfully')"

# Clean up
deactivate
rm -rf test-env
```

## Troubleshooting

### Common Issues

#### Permission Denied for libvirt
```bash
# Ensure user is in libvirt group
groups $USER
sudo usermod -a -G libvirt $USER
newgrp libvirt
```

#### Python Version Issues
```bash
# Install Python 3.11 on older systems
sudo add-apt-repository ppa:deadsnakes/ppa  # Ubuntu
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev
```

#### SELinux Issues (RHEL/CentOS)
```bash
# Allow libvirt access (if needed)
sudo setsebool -P virt_use_execmem 1
sudo setsebool -P virt_use_nfs 1
```

### Performance Issues
- **Slow VM creation**: Check storage I/O performance
- **High memory usage**: Monitor VM memory allocation
- **Network timeouts**: Verify firewall configuration

For additional troubleshooting, see the [Operations Guide](ops.md) and [Troubleshooting Guide](troubleshooting.md).
