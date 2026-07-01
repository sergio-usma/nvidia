# INNOVALABS — Deployment & Maintenance

## Service Management

### Starting Services

```bash
# Order matters - dependencies must be ready
sudo systemctl start docker

# Wait for Docker
sleep 5

# Start Ollama
sudo systemctl start ollama

# Wait for models to be available
sleep 10

# Start n8n
sudo systemctl start n8n

# Start dashboard
sudo systemctl start innovalabs-dashboard
```

### Checking Status

```bash
# All services
sudo systemctl status ollama n8n innovalabs-dashboard

# Quick check - ports listening
ss -tlnp | grep -E '11434|5678|8080'
```

### Restarting

```bash
# Restart specific service
sudo systemctl restart ollama
sudo systemctl restart n8n
sudo systemctl restart innovalabs-dashboard
```

## Headless Operation

### Disable Desktop GUI

```bash
# Switch to text-only mode
sudo systemctl set-default multi-user.target

# Stop desktop immediately
sudo systemctl stop gdm3 2>/dev/null
sudo systemctl stop lightdm 2>/dev/null

# Free memory (~1GB)
free -h
```

### SSH Access

```bash
# From Windows
ssh sergiok@192.168.1.50

# From Mac
ssh sergiok@192.168.1.50

# With key-based auth
ssh -i ~/.ssh/id_ed25519 sergiok@192.168.1.50
```

### SSH Keys Setup (Windows)

```powershell
# Generate key
ssh-keygen -t ed25519 -C "innovalabs"

# Copy to Jetson
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh sergiok@192.168.1.50 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

## Dashboard Usage

### Access URLs

```
Dashboard:        http://<JETSON_IP>:8080
Factory View:     http://<JETSON_IP>:8080/factory
n8n Editor:       http://<JETSON_IP>:5678
Ollama API:       http://<JETSON_IP>:11434
```

### Dashboard Features

**Monitoring Panel** (auto-refresh 5s):
- CPU: usage %, frequency, load average
- Memory: used/available/swap
- GPU: load %, frequency, temperatures
- Pipeline: current phase
- Services: Ollama, n8n status

**Control Panel**:
| Button | Action | Use Case |
|--------|--------|----------|
| Restart Ollama | `systemctl restart ollama` | Model not responding |
| Restart n8n | `systemctl restart n8n` | Workflow stuck |
| Trigger Pipeline | Execute workflow | Manual run |
| Free VRAM | Restart Ollama | Before heavy task |
| Max Performance | `jetson_clocks` | After reboot |
| Kill Writer | `pkill llama-cli` | Generation hung |

**Log Viewer**:
- System logs
- n8n logs
- Ollama logs

### API Endpoints

```bash
# System metrics
curl http://localhost:8080/api/system

# Pipeline status
curl http://localhost:8080/api/pipeline

# List stories
curl http://localhost:8080/api/stories

# Download story
curl http://localhost:8080/api/stories/H-1710432000000/download -o historia.md

# Control action
curl -X POST http://localhost:8080/api/control \
  -H "Content-Type: application/json" \
  -d '{"action":"restart_ollama","confirm":true}'
```

## Backup & Recovery

### Backup Scripts

```bash
# Create backup directory
BACKUP_DIR="/opt/innovalabs/backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup n8n data
cp -r ~/.n8n "$BACKUP_DIR/n8n_data"

# Backup config
cp /opt/innovalabs/config/.env "$BACKUP_DIR/"
cp /etc/systemd/system/n8n.service "$BACKUP_DIR/"

# Backup stories
cd /var/opt/innovalabs/historias
tar -czf "$BACKUP_DIR/historias_$(date +%Y%m%d).tar.gz" *.md

echo "Backup saved: $BACKUP_DIR"
```

### Automated Backups (Cron)

```bash
# Add to crontab
crontab -e

# Weekly backup (Sundays at 3 AM)
0 3 * * 0 cd /var/opt/innovalabs/historias && tar -czf /opt/innovalabs/backups/historias_$(date +\%Y\%m\%d).tar.gz *.md
```

### Restore from Backup

```bash
# Restore n8n
rm -rf ~/.n8n
cp -r /opt/innovalabs/backups/20240315/n8n_data ~/.n8n

# Restore stories
cd /var/opt/innovalabs/historias
tar -xzf /opt/innovalabs/backups/historias_20240315.tar.gz
```

## Maintenance Tasks

### Clean Temp Files

```bash
# Clean old temp files
find /tmp/innovalabs -type f -mtime +7 -delete
find /tmp/historia_* -type f -mtime +7 -delete 2>/dev/null

# Docker cleanup
docker system prune -f --volumes
```

### Update Models

```bash
# Update Ollama models
ollama pull glm-4.7-flash:latest
ollama pull deepseek-r1:8b
ollama pull nemotron-3-nano:latest

# Clean old versions
ollama list
# ollama rm old_model_name
```

### Update n8n

```bash
# Update n8n
npm install -g n8n

# Restart service
sudo systemctl restart n8n
```

## Monitoring Health

### Health Check Script

```bash
# Add to crontab
crontab -e

# Every hour - check services
0 * * * * curl -sf http://localhost:11434/api/tags > /dev/null || sudo systemctl restart ollama
0 * * * * curl -sf http://localhost:5678/healthz > /dev/null || sudo systemctl restart n8n
```

### Resource Monitoring

```bash
# Continuous monitoring
tegrastats --interval 1000

# Or use dashboard
# http://<JETSON_IP>:8080
```

## Troubleshooting

### Common Issues

| Issue | Symptom | Solution |
|-------|---------|----------|
| OOM | Writer fails | Restart Ollama, reduce concurrency |
| Model not loading | API timeout | Check disk space |
| Workflow stuck | No progress | Restart n8n |
| No stories generated | Empty output | Check Google Sheets queue |
| Dashboard offline | Can't access :8080 | Check service status |

### View Logs

```bash
# n8n
journalctl -u n8n -f --no-pager

# Ollama
docker logs ollama -f

# Dashboard
journalctl -u innovalabs-dashboard -f --no-pager

# All
journalctl -u n8n -u ollama -u innovalabs-dashboard -f --no-pager
```

### Emergency Recovery

```bash
# Stop all services
sudo systemctl stop n8n ollama innovalabs-dashboard

# Clear GPU memory
sudo rmmod nvmap
sudo nvpmodel -m 0
sudo jetson_clocks

# Start services
sudo systemctl start ollama
sleep 30
sudo systemctl start n8n
sudo systemctl start innovalabs-dashboard
```

## Security

### Basic Hardening

```bash
# Disable root login
sudo sed -i 's/#PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Change user password
passwd

# Install fail2ban
sudo apt install -y fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Firewall Rules

```bash
# Allow from local network only
sudo ufw allow from 192.168.1.0/24 to any port 5678
sudo ufw allow from 192.168.1.0/24 to any port 8080
sudo ufw allow ssh

# Deny everything else
sudo ufw default deny incoming
```

## Production Checklist

- [ ] n8n running on port 5678
- [ ] Ollama running on port 11434
- [ ] Dashboard running on port 8080
- [ ] Google Sheets configured
- [ ] All 4 models downloaded
- [ ] SSH keys configured
- [ ] Backup cron job active
- [ ] Health check cron active
- [ ] Firewall configured
- [ ] GPU clocks locked
- [ ] Headless mode enabled (optional)
