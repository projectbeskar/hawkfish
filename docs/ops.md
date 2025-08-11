# HawkFish Operations Guide

This guide covers operational aspects of running HawkFish in production environments.

## Backup and Recovery

### Backup Strategy

HawkFish provides built-in backup and restore functionality for operational data:

#### What's Included in Backups

- **SQLite Databases**: All metadata (profiles, systems, tasks, events, users)
- **Configuration**: Current settings and environment variables
- **Index Data**: Profiles and images metadata (not the large files)

#### What's NOT Included

- **Large Files**: ISO images, VM disk files (managed by libvirt)
- **VM State**: Running VM memory and disk state
- **Libvirt Definitions**: VM definitions on hypervisor hosts

### Creating Backups

#### Command Line

```bash
# Create immediate backup
hawkfish admin backup /backup/hawkfish-$(date +%Y%m%d-%H%M%S).tar.gz

# List available database files
hawkfish admin list-databases
```

#### Automated Backups

```bash
#!/bin/bash
# /etc/cron.daily/hawkfish-backup

BACKUP_DIR="/var/backups/hawkfish"
RETENTION_DAYS=30

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create backup
BACKUP_FILE="$BACKUP_DIR/hawkfish-$(date +%Y%m%d-%H%M%S).tar.gz"
hawkfish admin backup "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "Backup created: $BACKUP_FILE"
    
    # Remove old backups
    find "$BACKUP_DIR" -name "hawkfish-*.tar.gz" -mtime +$RETENTION_DAYS -delete
    
    # Log backup size
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "Backup size: $SIZE"
else
    echo "Backup failed!" >&2
    exit 1
fi
```

#### Docker/Kubernetes Backups

```yaml
# Kubernetes CronJob
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
            image: hawkfish/hawkfish-controller:latest
            command:
            - /bin/sh
            - -c
            - |
              hawkfish admin backup /backup/hawkfish-$(date +%Y%m%d-%H%M%S).tar.gz
              find /backup -name "hawkfish-*.tar.gz" -mtime +30 -delete
            volumeMounts:
            - name: backup-storage
              mountPath: /backup
            - name: hawkfish-state
              mountPath: /var/lib/hawkfish
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: hawkfish-backup-pvc
          - name: hawkfish-state
            persistentVolumeClaim:
              claimName: hawkfish-state-pvc
          restartPolicy: OnFailure
```

### Restoration

#### Basic Restore

```bash
# Restore from backup (stops current instance)
hawkfish admin restore /backup/hawkfish-20240115-140000.tar.gz

# Force restore (overwrite existing data)
hawkfish admin restore /backup/hawkfish-20240115-140000.tar.gz --force
```

#### Disaster Recovery Process

1. **Stop HawkFish Services**:
   ```bash
   # Systemd
   sudo systemctl stop hawkfish
   
   # Docker Compose
   docker-compose down
   
   # Kubernetes
   kubectl scale deployment hawkfish --replicas=0
   ```

2. **Restore Data**:
   ```bash
   # Restore from latest backup
   hawkfish admin restore /backup/latest-backup.tar.gz --force
   ```

3. **Verify Restoration**:
   ```bash
   # Check database integrity
   hawkfish admin list-databases
   
   # Test API access
   curl -f http://localhost:8080/redfish/v1/
   ```

4. **Restart Services**:
   ```bash
   # Start HawkFish
   sudo systemctl start hawkfish
   
   # Verify systems are accessible
   hawkfish systems list
   ```

## Audit Logging

### Overview

HawkFish maintains comprehensive audit logs for all state-changing operations:

- **Who**: User ID and session information
- **What**: Action performed and resource affected
- **When**: Timestamp with millisecond precision
- **How**: HTTP method, path, and status code
- **Result**: Success/failure and error details

### Accessing Audit Logs

#### API Access

```bash
# Get recent audit logs (admin required)
curl -H "X-Auth-Token: $TOKEN" \
  "http://localhost:8080/redfish/v1/Oem/HawkFish/Audit/Logs?limit=100"

# Filter by user
curl -H "X-Auth-Token: $TOKEN" \
  "http://localhost:8080/redfish/v1/Oem/HawkFish/Audit/Logs?user_id=admin"

# Filter by resource type
curl -H "X-Auth-Token: $TOKEN" \
  "http://localhost:8080/redfish/v1/Oem/HawkFish/Audit/Logs?resource_type=system"

# Get audit statistics
curl -H "X-Auth-Token: $TOKEN" \
  "http://localhost:8080/redfish/v1/Oem/HawkFish/Audit/Stats"
```

#### Log Analysis

```bash
# Export audit logs for analysis
curl -H "X-Auth-Token: $TOKEN" \
  "http://localhost:8080/redfish/v1/Oem/HawkFish/Audit/Logs?limit=10000" \
  | jq '.Members[]' > audit-export.jsonl

# Analyze with jq
# Most active users
jq -r '.UserId' audit-export.jsonl | sort | uniq -c | sort -nr

# Failed operations
jq 'select(.Success == false)' audit-export.jsonl

# Actions by resource type
jq -r '"\(.ResourceType):\(.Action)"' audit-export.jsonl | sort | uniq -c
```

### Audit Log Retention

```python
# Custom retention script
import sqlite3
from datetime import datetime, timedelta

def cleanup_old_audit_logs(db_path, retention_days=90):
    """Remove audit logs older than retention period."""
    cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
    
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        
        # Count logs to be deleted
        cursor.execute(
            "SELECT COUNT(*) FROM audit_log WHERE timestamp < ?",
            (cutoff_date.isoformat(),)
        )
        count = cursor.fetchone()[0]
        
        # Delete old logs
        cursor.execute(
            "DELETE FROM audit_log WHERE timestamp < ?",
            (cutoff_date.isoformat(),)
        )
        
        conn.commit()
        print(f"Deleted {count} old audit log entries")
```

## Database Migration

### Schema Evolution

HawkFish handles database schema changes through migration scripts:

```python
# Example migration for new column
async def migrate_v0_6_to_v0_7():
    """Migration from v0.6 to v0.7 schema."""
    async with aiosqlite.connect(db_path) as db:
        # Add new column if it doesn't exist
        try:
            await db.execute("ALTER TABLE hf_systems ADD COLUMN host_id TEXT")
            await db.commit()
            logger.info("Added host_id column to hf_systems")
        except sqlite3.OperationalError:
            # Column already exists
            pass
        
        # Update existing records with default host
        await db.execute(
            "UPDATE hf_systems SET host_id = 'default' WHERE host_id IS NULL"
        )
        await db.commit()
```

### Manual Migration

```bash
# Check current schema version
sqlite3 /var/lib/hawkfish/hawkfish.db \
  "SELECT name FROM sqlite_master WHERE type='table';"

# Backup before migration
hawkfish admin backup pre-migration-backup.tar.gz

# Run migration (built into controller startup)
python -m hawkfish_controller --migrate

# Verify migration
hawkfish admin list-databases
```

## Performance Monitoring

### Key Metrics

HawkFish exposes Prometheus metrics for monitoring:

#### API Metrics

```bash
# Request rate and latency
hawkfish_api_requests_total
hawkfish_api_request_duration_seconds

# Error rates
hawkfish_api_errors_total{status="4xx"}
hawkfish_api_errors_total{status="5xx"}
```

#### System Metrics

```bash
# Systems and resources
hawkfish_systems_total
hawkfish_systems_by_state{state="running"}
hawkfish_profiles_total
hawkfish_images_total

# Task processing
hawkfish_tasks_total{state="completed"}
hawkfish_tasks_duration_seconds
```

#### Connection Pool Metrics

```bash
# Get pool metrics
curl http://localhost:8080/redfish/v1/libvirt-pool-metrics

# Example response
{
  "qemu:///system": {
    "pool_size": 5,
    "active_connections": 3,
    "checkout_count": 1247,
    "failure_count": 2,
    "reconnect_count": 1
  }
}
```

### Performance Tuning

#### Connection Pool Optimization

```bash
# Increase pool size for high load
export HF_LIBVIRT_POOL_MIN=5
export HF_LIBVIRT_POOL_MAX=20
export HF_LIBVIRT_POOL_TTL_SEC=600
```

#### Rate Limiting Configuration

```python
# Adjust rate limits in middleware
from hawkfish_controller.services.rate_limit import global_rate_limiter

# Configure per-user limits
global_rate_limiter.configure(
    default_rate=100,  # requests per minute
    burst_rate=200,    # burst allowance
    admin_rate=1000    # higher limit for admins
)
```

#### Database Optimization

```bash
# SQLite optimization
sqlite3 /var/lib/hawkfish/hawkfish.db << EOF
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
PRAGMA temp_store=memory;
VACUUM;
ANALYZE;
EOF
```

### Performance Testing

#### Load Testing

```bash
# Run performance tests
cd tests/performance/
python -m pytest test_load.py::test_service_root_load -v

# Custom load test
python test_load.py  # Run standalone
```

#### Benchmark Results

Target performance metrics:

| Endpoint | Target RPS | Target Latency (95th) |
|----------|------------|----------------------|
| Service Root | 200+ | < 100ms |
| Systems List | 50+ | < 500ms |
| Power Actions | 20+ | < 1000ms |
| System Creation | 5+ | < 10s |

## Security Operations

### Access Control

#### User Management

```bash
# Create admin user
curl -X POST http://localhost:8080/redfish/v1/AccountService/Accounts \
  -H "Content-Type: application/json" \
  -d '{
    "UserName": "sysadmin",
    "Password": "secure-password",
    "RoleId": "Administrator"
  }'

# Create read-only user
curl -X POST http://localhost:8080/redfish/v1/AccountService/Accounts \
  -H "Content-Type: application/json" \
  -d '{
    "UserName": "readonly",
    "Password": "view-password",
    "RoleId": "ReadOnly"
  }'
```

#### Session Management

```bash
# List active sessions
curl -H "X-Auth-Token: $ADMIN_TOKEN" \
  http://localhost:8080/redfish/v1/SessionService/Sessions

# Revoke specific session
curl -X DELETE -H "X-Auth-Token: $ADMIN_TOKEN" \
  http://localhost:8080/redfish/v1/SessionService/Sessions/{session-id}
```

### Security Hardening

#### TLS Configuration

```bash
# Generate production certificates
openssl req -x509 -newkey rsa:4096 -keyout server.key -out server.crt \
  -days 365 -nodes -subj "/CN=hawkfish.example.com"

# Configure custom TLS
export HF_DEV_TLS=custom
export HF_TLS_CERT=/etc/ssl/certs/hawkfish.crt
export HF_TLS_KEY=/etc/ssl/private/hawkfish.key
```

#### Network Security

```bash
# Firewall rules (UFW)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 10.0.0.0/8 to any port 8080  # Internal only
sudo ufw enable

# Network isolation
# Run HawkFish on management network
export HF_API_HOST=10.0.100.10
```

#### File System Security

```bash
# Secure state directory
sudo chmod 750 /var/lib/hawkfish
sudo chown hawkfish:hawkfish /var/lib/hawkfish

# SELinux context (if applicable)
sudo semanage fcontext -a -t admin_home_t "/var/lib/hawkfish(/.*)?"
sudo restorecon -R /var/lib/hawkfish
```

### Security Monitoring

#### Failed Login Detection

```bash
# Monitor failed authentication attempts
grep "authentication failed" /var/log/hawkfish/hawkfish.log

# Failed login alerting
tail -f /var/log/hawkfish/hawkfish.log | grep -i "auth.*failed" | \
  while read line; do
    echo "$(date): Failed auth detected: $line" | \
    mail -s "HawkFish Security Alert" admin@example.com
  done
```

#### Security Audit

```python
# Security audit script
import asyncio
from hawkfish_controller.services.audit import audit_logger

async def security_audit():
    """Generate security audit report."""
    
    # Get recent failed operations
    failed_ops = await audit_logger.get_audit_logs(
        limit=1000,
        success=False,
        start_time=(datetime.utcnow() - timedelta(days=7)).isoformat()
    )
    
    print(f"Failed operations in last 7 days: {len(failed_ops['logs'])}")
    
    # Analyze failed logins
    auth_failures = [
        log for log in failed_ops['logs'] 
        if log['action'] == 'login' and log['status_code'] == 401
    ]
    
    print(f"Failed login attempts: {len(auth_failures)}")
    
    # Check for privilege escalation attempts
    priv_attempts = [
        log for log in failed_ops['logs']
        if log['status_code'] == 403
    ]
    
    print(f"Privilege escalation attempts: {len(priv_attempts)}")
```

## Health Monitoring

### Health Checks

#### Application Health

```bash
# Basic health check
curl -f http://localhost:8080/redfish/v1/ || echo "API unhealthy"

# Detailed health status
curl http://localhost:8080/redfish/v1/health 2>/dev/null | jq .
```

#### Libvirt Connectivity

```bash
# Test libvirt connections
virsh -c qemu:///system list --all

# Check multiple hosts
for host in host1 host2 host3; do
  echo "Testing $host..."
  virsh -c qemu+ssh://user@$host/system list --brief
done
```

#### Database Health

```bash
# Check database integrity
sqlite3 /var/lib/hawkfish/hawkfish.db "PRAGMA integrity_check;"

# Database size and usage
sqlite3 /var/lib/hawkfish/hawkfish.db "
  SELECT 
    name,
    COUNT(*) as records
  FROM sqlite_master 
  WHERE type='table' 
  GROUP BY name;
"
```

### Alerting

#### Prometheus Alerts

```yaml
# prometheus-alerts.yml
groups:
  - name: hawkfish
    rules:
      - alert: HawkFishDown
        expr: up{job="hawkfish"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "HawkFish API is down"

      - alert: HighErrorRate
        expr: rate(hawkfish_api_errors_total[5m]) > 0.1
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "High API error rate: {{ $value }}/sec"

      - alert: SlowRequests
        expr: histogram_quantile(0.95, rate(hawkfish_api_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "95th percentile latency is {{ $value }}s"

      - alert: ConnectionPoolExhausted
        expr: hawkfish_libvirt_pool_active_connections >= hawkfish_libvirt_pool_max_size * 0.9
        for: 2m
        labels:
          severity: warning
        annotations:
          summary: "Libvirt connection pool nearly exhausted"
```

#### Custom Health Monitoring

```python
#!/usr/bin/env python3
"""Custom health monitoring script for HawkFish."""

import asyncio
import time
import smtplib
from email.mime.text import MIMEText

class HealthMonitor:
    def __init__(self, hawkfish_url, alert_email):
        self.hawkfish_url = hawkfish_url
        self.alert_email = alert_email
        self.last_alert = {}
    
    async def check_api_health(self):
        """Check API responsiveness."""
        try:
            async with httpx.AsyncClient() as client:
                start_time = time.time()
                response = await client.get(f"{self.hawkfish_url}/redfish/v1/")
                latency = time.time() - start_time
                
                if response.status_code != 200:
                    return False, f"API returned {response.status_code}"
                
                if latency > 5.0:
                    return False, f"API latency too high: {latency:.2f}s"
                
                return True, f"API healthy (latency: {latency:.3f}s)"
        
        except Exception as e:
            return False, f"API check failed: {e}"
    
    async def check_libvirt_connectivity(self):
        """Check libvirt host connectivity."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.hawkfish_url}/redfish/v1/libvirt-pool-metrics"
                )
                
                if response.status_code != 200:
                    return False, "Cannot get pool metrics"
                
                metrics = response.json()
                failed_hosts = []
                
                for host_uri, stats in metrics.items():
                    if stats.get('failure_count', 0) > stats.get('checkout_count', 1) * 0.1:
                        failed_hosts.append(host_uri)
                
                if failed_hosts:
                    return False, f"High failure rate on hosts: {failed_hosts}"
                
                return True, f"All {len(metrics)} hosts healthy"
        
        except Exception as e:
            return False, f"Libvirt check failed: {e}"
    
    def send_alert(self, subject, message):
        """Send email alert with rate limiting."""
        now = time.time()
        if now - self.last_alert.get(subject, 0) < 300:  # 5 minute cooldown
            return
        
        try:
            msg = MIMEText(message)
            msg['Subject'] = f"HawkFish Alert: {subject}"
            msg['From'] = "hawkfish@example.com"
            msg['To'] = self.alert_email
            
            # Configure SMTP as needed
            # smtp = smtplib.SMTP('localhost')
            # smtp.send_message(msg)
            # smtp.quit()
            
            print(f"ALERT: {subject} - {message}")
            self.last_alert[subject] = now
        
        except Exception as e:
            print(f"Failed to send alert: {e}")
    
    async def run_checks(self):
        """Run all health checks."""
        checks = [
            ("API Health", self.check_api_health()),
            ("Libvirt Connectivity", self.check_libvirt_connectivity()),
        ]
        
        for check_name, check_coro in checks:
            healthy, message = await check_coro
            
            if healthy:
                print(f"✓ {check_name}: {message}")
            else:
                print(f"✗ {check_name}: {message}")
                self.send_alert(check_name, message)

async def main():
    monitor = HealthMonitor(
        hawkfish_url="http://localhost:8080",
        alert_email="admin@example.com"
    )
    
    while True:
        await monitor.run_checks()
        await asyncio.sleep(60)  # Check every minute

if __name__ == "__main__":
    asyncio.run(main())
```

## Maintenance Procedures

### Routine Maintenance

#### Daily Tasks

```bash
#!/bin/bash
# Daily maintenance script

echo "=== Daily HawkFish Maintenance ==="

# Check disk space
df -h /var/lib/hawkfish

# Backup critical data
hawkfish admin backup /backup/daily/hawkfish-$(date +%Y%m%d).tar.gz

# Check for failed tasks
hawkfish tasks list --state Exception

# Verify libvirt connectivity
hawkfish systems list >/dev/null && echo "✓ Systems accessible" || echo "✗ Systems check failed"

# Clean up old logs (if using file logging)
find /var/log/hawkfish -name "*.log" -mtime +7 -delete

echo "=== Maintenance Complete ==="
```

#### Weekly Tasks

```bash
#!/bin/bash
# Weekly maintenance script

echo "=== Weekly HawkFish Maintenance ==="

# Database maintenance
sqlite3 /var/lib/hawkfish/hawkfish.db "VACUUM; ANALYZE;"

# Clean up old audit logs (keep 90 days)
python3 -c "
import sqlite3
from datetime import datetime, timedelta

cutoff = datetime.utcnow() - timedelta(days=90)
with sqlite3.connect('/var/lib/hawkfish/hawkfish.db') as conn:
    cursor = conn.cursor()
    cursor.execute('DELETE FROM audit_log WHERE timestamp < ?', (cutoff.isoformat(),))
    print(f'Cleaned up {cursor.rowcount} old audit records')
    conn.commit()
"

# Image catalog cleanup
hawkfish images list | grep "unused" | while read image_id _; do
  echo "Removing unused image: $image_id"
  hawkfish image-rm "$image_id"
done

# Generate weekly report
echo "=== Weekly Statistics ==="
hawkfish admin audit-stats

echo "=== Weekly Maintenance Complete ==="
```

### Upgrade Procedures

#### Minor Version Upgrades

```bash
#!/bin/bash
# Minor version upgrade (e.g., 0.7.0 -> 0.7.1)

echo "Starting HawkFish minor upgrade..."

# 1. Backup current state
hawkfish admin backup /backup/pre-upgrade-$(date +%Y%m%d-%H%M%S).tar.gz

# 2. Stop service
sudo systemctl stop hawkfish

# 3. Upgrade package
pip install --upgrade hawkfish-controller

# 4. Start service (migrations run automatically)
sudo systemctl start hawkfish

# 5. Verify upgrade
sleep 10
curl -f http://localhost:8080/redfish/v1/ && echo "Upgrade successful"
```

#### Major Version Upgrades

```bash
#!/bin/bash
# Major version upgrade (e.g., 0.6.x -> 0.7.x)

echo "Starting HawkFish major upgrade..."

# 1. Read upgrade notes
echo "Please review upgrade notes at docs/upgrade-to-v0.7.md"
read -p "Continue? (y/N) " -n 1 -r
[[ ! $REPLY =~ ^[Yy]$ ]] && exit 1

# 2. Full backup
hawkfish admin backup /backup/major-upgrade-$(date +%Y%m%d-%H%M%S).tar.gz

# 3. Export configuration
env | grep ^HF_ > /backup/hawkfish-env-backup.sh

# 4. Stop service
sudo systemctl stop hawkfish

# 5. Upgrade package
pip install --upgrade hawkfish-controller==0.7.0

# 6. Run manual migrations if needed
python -m hawkfish_controller --migrate

# 7. Update configuration if needed
# (Review new settings, update environment variables)

# 8. Start service
sudo systemctl start hawkfish

# 9. Comprehensive verification
hawkfish systems list
hawkfish profiles list
hawkfish images list

echo "Major upgrade complete. Please test thoroughly."
```

This completes the comprehensive operations guide for HawkFish, covering all aspects of production operations including backup/recovery, audit logging, monitoring, security, and maintenance procedures.
