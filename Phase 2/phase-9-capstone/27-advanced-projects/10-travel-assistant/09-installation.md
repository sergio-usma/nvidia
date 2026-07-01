# Tourism Intelligence - Installation Guide

## Prerequisites

Before installing, ensure you have:

- Jetson AGX Orin with JetPack 6.2
- Python 3.12 (via pyenv)
- Ollama running with models
- Google Cloud service account credentials
- 20GB free storage

## System Requirements

- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 20GB for data and models
- **Network**: Internet connection for scraping

## Installation Steps

### 1. Create Project Directory

```bash
# Create project directory
sudo mkdir -p /opt/tourism-intel
sudo chown $USER:$USER /opt/tourism-intel

cd /opt/tourism-intel
```

### 2. Setup Virtual Environment

```bash
# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

### 3. Install Dependencies

```bash
pip install flask flask-cors requests beautifulsoup4 lxml
pip install playwright google-api-python-client google-auth
pip install schedule python-dotenv
```

### 4. Install Playwright

```bash
playwright install chromium
playwright install-deps
```

### 5. Create Directory Structure

```bash
mkdir -p /opt/tourism-intel/{config,data/{hotels,airlines,news,trends,reports,alerts},logs,scraper,agents,scheduler,sheets,dashboard}
mkdir -p /opt/tourism-intel/data/agents
```

### 6. Configuration Files

Create `/opt/tourism-intel/.env`:

```bash
# API Configuration
export FLASK_APP=dashboard/main.py
export FLASK_ENV=production

# Ollama
export OLLAMA_HOST=http://localhost:11434

# Google Sheets
export SPREADSHEET_ID=your_spreadsheet_id_here
export GOOGLE_APPLICATION_CREDENTIALS=/opt/tourism-intel/config/sheets-credentials.json

# Discord (optional)
export DISCORD_WEBHOOK_URL=your_webhook_url_here
```

Create `/opt/tourism-intel/config/sources.py`:

```python
# Tourism sources configuration

CITIES = {
    "bogota": {"name": "Bogotá", "code": "BOG"},
    "medellin": {"name": "Medellín", "code": "MDE"},
    "cartagena": {"name": "Cartagena", "code": "CTG"},
    "cali": {"name": "Cali", "code": "CLO"},
    "barranquilla": {"name": "Barranquilla", "code": "BAQ"},
    "santa_marta": {"name": "Santa Marta", "code": "SMR"}
}

HOTEL_SOURCES = ["booking", "tripadvisor", "expedia"]
AIRLINE_SOURCES = ["avianca", "latam"]
NEWS_SOURCES = ["el_tiempo", "portafolio", "semana"]

SCRAPING_INTERVAL = 900  # 15 minutes
```

### 7. Ollama Models

Ensure these models are installed:

```bash
# Pull required models
ollama pull qwen2.5-coder:14b
ollama pull llama3.2:3b
ollama pull deepseek-r1:8b
ollama pull glm-4.7-flash:latest
```

### 8. Google Sheets Setup

1. Create Google Cloud project
2. Enable Sheets and Drive APIs
3. Create service account
4. Download credentials JSON
5. Save as `/opt/tourism-intel/config/sheets-credentials.json`
6. Create spreadsheet and share with service account
7. Copy spreadsheet ID to `.env`

### 9. Create Startup Scripts

Create `/opt/tourism-intel/start.sh`:

```bash
#!/bin/bash
cd /opt/tourism-intel
source venv/bin/activate
source .env

# Start dashboard (runs API and web)
python dashboard/main.py > logs/dashboard.log 2>&1 &

# Start scheduler
python scheduler/main.py > logs/scheduler.log 2>&1 &

echo "Tourism Intelligence started"
```

Create `/opt/tourism-intel/stop.sh`:

```bash
#!/bin/bash
pkill -f "tourism-intel"
pkill -f "dashboard/main.py"
pkill -f "scheduler/main.py"
echo "Tourism Intelligence stopped"
```

```bash
chmod +x /opt/tourism-intel/*.sh
```

### 10. Systemd Service

Create `/etc/systemd/system/tourism-intel.service`:

```ini
[Unit]
Description=Tourism Intelligence Platform
After=network.target ollama.service

[Service]
Type=simple
User=sergiok
WorkingDirectory=/opt/tourism-intel
Environment=PATH=/opt/tourism-intel/venv/bin:/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/tourism-intel/start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable tourism-intel
sudo systemctl start tourism-intel
```

## Verification

### Check Services

```bash
# Check if dashboard is running
curl http://localhost:8095/api/stats

# Check if scheduler is running
tail -f /opt/tourism-intel/logs/scheduler.log

# Check agents
curl http://localhost:8095/api/agents
```

### Expected Output

```json
{
  "total_hotels": 150,
  "cycle": 10,
  "cities": {
    "bogota": 50,
    "medellin": 35,
    "cartagena": 30,
    "cali": 20,
    "barranquilla": 10,
    "santa_marta": 5
  }
}
```

## Access

| Service | URL |
|---------|-----|
| Dashboard | http://jetson:8095 |
| API | http://jetson:8095/api/ |
| Hotels | http://jetson:8095/api/hotels |
| Stats | http://jetson:8095/api/stats |

## Nginx Proxy (Optional)

```nginx
server {
    listen 8095;
    server_name jetson;

    location / {
        proxy_pass http://127.0.0.1:8095;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting

### No hotels scraped

```bash
# Check logs
tail -f /opt/tourism-intel/logs/scheduler.log

# Test scraping manually
cd /opt/tourism-intel
source venv/bin/activate
python -c "
from scraper.main import Orchestrator
o = Orchestrator()
o.run_full_cycle()
"
```

### Google Sheets errors

```bash
# Verify credentials
python -c "
from google.oauth2 import service_account
creds = service_account.Credentials.from_service_account_file(
    '/opt/tourism-intel/config/sheets-credentials.json'
)
print('Credentials OK')
"
```

### Ollama connection issues

```bash
# Check Ollama
curl http://localhost:11434/api/tags

# Restart if needed
sudo systemctl restart ollama
```

## Maintenance

### Backup Data

```bash
# Backup to external drive
rsync -av /opt/tourism-intel/data/ /backup/tourism-data/
```

### Clean Old Data

```bash
# Remove data older than 90 days
find /opt/tourism-intel/data -type f -mtime +90 -delete
```

### Update Models

```bash
# Update Ollama models
ollama pull qwen2.5-coder:14b
ollama pull llama3.2:3b
ollama pull deepseek-r1:8b
```

## Usage

### Add Manual Task

```bash
curl -X POST http://localhost:8095/api/scheduler/run \
  -H "Content-Type: application/json" \
  -d '{"task": "scrape"}'
```

### Get City Data

```bash
curl http://localhost:8095/api/hotels/bogota
```

### Force Report

```bash
curl -X POST http://localhost:8095/api/scheduler/run \
  -H "Content-Type: application/json" \
  -d '{"task": "report"}'
```

## Security

- Keep `sheets-credentials.json` private
- Use environment variables for secrets
- Restrict network access to local network
- Regularly update dependencies

## Monitoring

```bash
# Watch logs
watch -n 5 'curl -s http://localhost:8095/api/stats | python -m json.tool'

# Check disk usage
df -h /opt/tourism-intel

# Check memory
free -h
```

## Summary

| Component | Port | Status |
|-----------|------|--------|
| Dashboard | 8095 | Required |
| API | 8095 | Required |
| Scheduler | Background | Required |
| Ollama | 11434 | Required |
| Sheets | API | Required |

## Quick Start

```bash
# One-line start
cd /opt/tourism-intel && source venv/bin/activate && source .env && python dashboard/main.py & python scheduler/main.py

# Access dashboard
# Open http://jetson:8095 in browser
```

Project 10 (Tourism Intelligence) is now complete with all 9 files!
