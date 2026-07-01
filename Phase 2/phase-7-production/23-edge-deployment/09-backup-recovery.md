# Backup & Recovery

Implement comprehensive backup and recovery strategies for your AI services.

## Backup Strategy Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Backup Architecture                         │
│                                                                  │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────────┐  │
│  │  Source    │────▶│   Backup    │────▶│   Offsite       │  │
│  │  (Jetson)  │     │   (Local)   │     │   (Remote)      │  │
│  └─────────────┘     └─────────────┘     └─────────────────┘  │
│         │                   │                    │             │
│         │                   │                    │             │
│    ┌────┴────┐        ┌────┴────┐          ┌────┴────┐       │
│    │ Models  │        │ Config  │          │ Config  │       │
│    │ Data   │        │ Logs    │          │ Models  │       │
│    └─────────┘        └─────────┘          └─────────┘       │
└─────────────────────────────────────────────────────────────────┘
```

## What to Backup

| Item | Priority | Size | Frequency |
|------|----------|------|----------|
| Ollama Models | Critical | 10-50GB | Weekly |
| User Data | Critical | 1-10GB | Daily |
| Configuration | High | KB | Daily |
| Logs | Medium | GB | Weekly |
| System Image | High | 30GB | Monthly |

## Backup Scripts

### Model Backup

```bash
#!/bin/bash
# backup-models.sh

BACKUP_DIR="/backup/models"
DATE=$(date +%Y%m%d)
SOURCE_DIR="/root/.ollama/models"

mkdir -p "$BACKUP_DIR"

echo "Starting model backup: $DATE"

# Create compressed backup
tar -czvf "$BACKUP_DIR/ollama-models-$DATE.tar.gz" \
    -C "$SOURCE_DIR" .

# Keep only last 7 backups
cd "$BACKUP_DIR"
ls -t ollama-models-*.tar.gz | tail -n +8 | xargs -r rm

echo "Model backup complete: ollama-models-$DATE.tar.gz"
```

### Configuration Backup

```bash
#!/bin/bash
# backup-config.sh

BACKUP_DIR="/backup/config"
DATE=$(date +%Y%m%d)

mkdir -p "$BACKUP_DIR"

# Backup critical configs
tar -czvf "$BACKUP_DIR/config-$DATE.tar.gz" \
    /home/jetson/ai-stack/ \
    /etc/nginx/ \
    /etc/systemd/system/ai-*.service \
    ~/.env

echo "Config backup complete"
```

### Complete Backup

```bash
#!/bin/bash
# backup-all.sh

BACKUP_ROOT="/backup"
DATE=$(date +%Y%m%d-%H%M%S)

# Create timestamped backup directory
mkdir -p "$BACKUP_ROOT/$DATE"

# Run individual backups
bash /home/jetson/backup/backup-models.sh
bash /home/jetson/backup/backup-config.sh

# Create overall archive
cd "$BACKUP_ROOT"
tar -czvf "full-backup-$DATE.tar.gz" "$DATE/"

# Upload to remote (if configured)
if [ -n "$REMOTE_BACKUP_HOST" ]; then
    rsync -avz "$BACKUP_ROOT/full-backup-$DATE.tar.gz" \
        "$REMOTE_BACKUP_HOST:/backups/jetson/"
fi

echo "Full backup complete: $DATE"
```

## Automated Backup Schedule

### Cron Configuration

```bash
# Edit crontab
crontab -e

# Add these lines
# Daily at 2 AM - Models backup
0 2 * * * /home/jetson/backup/backup-models.sh

# Daily at 3 AM - Config backup
0 3 * * * /home/jetson/backup/backup-config.sh

# Weekly on Sunday at 4 AM - Full backup
0 4 * * 0 /home/jetson/backup/backup-all.sh
```

### Systemd Timers

Create `/etc/systemd/system/backup.timer`:

```ini
[Unit]
Description=AI Stack Backup Timer

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Create `/etc/systemd/system/backup.service`:

```ini
[Unit]
Description=AI Stack Backup Service
After=network.target

[Service]
Type=oneshot
ExecStart=/home/jetson/backup/backup-all.sh
User=jetson
```

Enable:

```bash
sudo systemctl enable backup.timer
sudo systemctl start backup.timer
```

## Offsite Backup

### Rsync to Remote Server

```bash
#!/bin/bash
# sync-offsite.sh

REMOTE_USER="backup"
REMOTE_HOST="backup-server.example.com"
REMOTE_DIR="/backup/jetson"

# Sync backup directory
rsync -avz --delete \
    --exclude='*.tmp' \
    /backup/ \
    $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/

echo "Offsite sync complete"
```

### Rclone Configuration

```bash
# Install rclone
curl https://rclone.org/install.sh | sudo bash

# Configure rclone
rclone config

# Create backup script using rclone
rclone copy /backup s3:mybucket/jetson-backup \
    --progress \
    --transfers 4
```

## Recovery Procedures

### Restore Models

```bash
# List available backups
ls -lh /backup/models/

# Restore specific backup
sudo systemctl stop ollama

tar -xzvf /backup/models/ollama-models-20241201.tar.gz \
    -C /root/.ollama/models/

sudo systemctl start ollama

# Verify
curl http://localhost:11434/api/tags
```

### Restore Configuration

```bash
# Backup current config first
cp -r /home/jetson/ai-stack /home/jetson/ai-stack.bak

# Restore from backup
tar -xzvf /backup/config/config-20241201.tar.gz -C /

# Restart services
sudo systemctl restart ollama nginx
```

### Complete System Restore

```bash
# Extract full backup
tar -xzvf /backup/full-backup-20241201.tar.gz -C /

# Restore services
sudo systemctl daemon-reload
sudo systemctl restart ai-stack

# Verify all services
/home/jetson/ai-stack/health.sh
```

## Disaster Recovery

### Recovery Time Objectives

| Component | RTO | RPO |
|-----------|-----|-----|
| Models | 2 hours | 24 hours |
| Config | 1 hour | 24 hours |
| User Data | 1 hour | 1 hour |
| Full System | 4 hours | 1 week |

### DR Script

```bash
#!/bin/bash
# disaster-recovery.sh

set -e

echo "=== Disaster Recovery Mode ==="
echo "This will restore the system from backup"
echo ""

# Verify backup exists
LATEST_BACKUP=$(ls -t /backup/full-backup-*.tar.gz | head -1)
if [ -z "$LATEST_BACKUP" ]; then
    echo "ERROR: No backup found"
    exit 1
fi

echo "Using backup: $LATEST_BACKUP"
read -p "Continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Aborted"
    exit 0
fi

# Stop services
echo "Stopping services..."
sudo systemctl stop ollama nginx ai-stack

# Restore
echo "Restoring from backup..."
tar -xzvf "$LATEST_BACKUP" -C /

# Restart services
echo "Restarting services..."
sudo systemctl daemon-reload
sudo systemctl start ollama nginx ai-stack

# Verify
echo "Verifying services..."
sleep 10
curl -s http://localhost:11434/api/tags && echo "Ollama: OK"
curl -s http://localhost:5000/health && echo "API: OK"

echo "Disaster recovery complete"
```

## Backup Verification

### Test Restore

```bash
#!/bin/bash
# test-restore.sh

TEST_DIR="/tmp/restore-test"

mkdir -p "$TEST_DIR"

# Extract to test location
tar -xzvf /backup/models/ollama-models-20241201.tar.gz -C "$TEST_DIR"

# Verify contents
echo "Checking model files..."
ls -la "$TEST_DIR/models/"

# Clean up
rm -rf "$TEST_DIR"

echo "Restore test complete"
```

## Next Steps

- [Scaling](./10-scaling.md) - Scale your deployment
- [Monitoring](./11-monitoring.md) - Track performance
