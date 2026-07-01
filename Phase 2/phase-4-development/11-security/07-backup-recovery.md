# Backup and Recovery

This guide covers backup and recovery strategies for Jetson AGX Orin.

## System Backup

```bash
# Full system backup with rsync
sudo rsync -aAXv \
    --exclude={"/dev/*","/proc/*","/sys/*","/tmp/*","/run/*","/mnt/*","/media/*","/lost+found"} \
    / /backup/rootfs

# Create compressed archive
sudo tar -czpvf system-backup.tar.gz --exclude=/proc --exclude=/sys \
    --exclude=/dev --exclude=/run --exclude=/tmp --exclude=/mnt /
```

## Database Backup

### PostgreSQL

```bash
# Dump database
pg_dump -U postgres mydb > backup.sql

# Compressed dump
pg_dump -U postgres mydb | gzip > backup.sql.gz

# Restore
psql -U postgres mydb < backup.sql

# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
pg_dump -U postgres mydb | gzip > /backups/mydb_$DATE.sql.gz
find /backups -type f -mtime +7 -delete
```

### MySQL

```bash
# Dump
mysqldump -u root -p mydb > backup.sql

# Restore
mysql -u root -p mydb < backup.sql
```

### MongoDB

```bash
# Dump
mongodump --db=mydb --out=/backups/

# Restore
mongorestore /backups/mydb/
```

## Docker Volumes

```bash
# Backup volume
docker run --rm -v myvolume:/data -v $(pwd):/backup alpine tar cvf /backup/volume-backup.tar -C /data .

# Restore volume
docker volume create myvolume
docker run --rm -v myvolume:/data -v $(pwd):/backup alpine tar xvf /backup/volume-backup.tar -C /data
```

## Configuration Backup

```bash
# Backup config files
tar -czpvf configs-backup.tar.gz \
    /etc/nginx/ \
    /etc/systemd/ \
    /home/*/.config/ \
    ~/.ssh/
```

## Model Files

```bash
# Backup AI models
tar -czpvf models-backup.tar.gz -C /models .
rsync -av /models/ /backup/models/
```

## Incremental Backup

```bash
# Using rdiff-backup
rdiff-backup /home /backup/home

# Restore
rdiff-backup --restore-at-time 2D /backup/home /home_restored
```

## Cloud Backup

### AWS S3

```bash
# Install AWS CLI
pip install awscli

# Configure
aws configure

# Sync to S3
aws s3 sync /data s3://my-bucket/backups/

# Download
aws s3 sync s3://my-bucket/backups/ /restore/
```

### rsync to remote

```bash
# Backup to remote server
rsync -avz -e ssh --progress /data user@remote:/backup/

# With compression
rsync -avzE --delete /data user@remote:/backup/
```

## Backup Rotation

```bash
#!/bin/bash
# backup-rotation.sh

BACKUP_DIR="/backups"
DAILY=7
WEEKLY=4
MONTHLY=6

# Daily
cp /data/backup.tar.gz $BACKUP_DIR/daily/

# Weekly (if Sunday)
if [ $(date +%u) -eq 7 ]; then
    cp $BACKUP_DIR/daily/backup.tar.gz $BACKUP_DIR/weekly/
fi

# Monthly (if 1st)
if [ $(date +%d) -eq 01 ]; then
    cp $BACKUP_DIR/daily/backup.tar.gz $BACKUP_DIR/monthly/
fi

# Cleanup
find $BACKUP_DIR/daily -mtime +$DAILY -delete
find $BACKUP_DIR/weekly -mtime +$((WEEKLY*7)) -delete
find $BACKUP_DIR/monthly -mtime +$((MONTHLY*30)) -delete
```

## Disaster Recovery

```bash
#!/bin/bash
# recover.sh

# Stop services
sudo systemctl stop nginx
sudo systemctl stop myapp

# Restore system
sudo tar -xzpvf system-backup.tar.gz -C /

# Restart services
sudo systemctl start nginx
sudo systemctl start myapp
```

## RAID

```bash
# Create RAID 1
sudo mdadm --create --verbose /dev/md0 --level=1 --raid-devices=2 /dev/sda1 /dev/sdb1

# Monitor
sudo mdadm --detail /dev/md0
```

## Timeshift

```bash
sudo apt install timeshift

# Create snapshot
sudo timeshift --create --comments "Before update"

# Restore
sudo timeshift --restore
```

## Application Backup

```python
# Python backup script
import subprocess
import os
from datetime import datetime

def backup_application():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Database
    subprocess.run([
        'pg_dump', '-U', 'postgres', 'mydb'
    ], stdout=open(f'backup_{timestamp}.sql', 'w'))
    
    # Files
    subprocess.run(['tar', '-czf', f'files_{timestamp}.tar.gz', './data'])
    
    # Upload to cloud
    subprocess.run([
        'aws', 's3', 'sync', '.', f's3://mybucket/{timestamp}/'
    ])

if __name__ == '__main__':
    backup_application()
```

## Backup Verification

```bash
# Test restore in VM
# Verify checksums
sha256sum backup.tar.gz > backup.sha256

# Verify
sha256sum -c backup.sha256
```

## Cron Scheduling

```bash
# Edit crontab
crontab -e

# Daily at 2am
0 2 * * * /path/to/backup.sh

# Weekly on Sunday at 3am
0 3 * * 0 /path/to/weekly-backup.sh
```
