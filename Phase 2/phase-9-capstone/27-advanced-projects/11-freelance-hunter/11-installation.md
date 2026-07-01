# Freelance Hunter - Installation Guide

## Prerequisites

Before installing, ensure you have:

- Jetson AGX Orin with JetPack 6.2
- Python 3.12 (via pyenv)
- Ollama running with models
- Google Cloud service account credentials (for Sheets)
- Discord bot token (optional, for Discord control)
- 10GB free storage

## System Requirements

- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 10GB for data and models
- **Network**: Internet connection for scraping

## Installation Steps

### 1. Create Project Directory

```bash
# Create project directory
sudo mkdir -p /opt/freelance-hunter
sudo chown $USER:$USER /opt/freelance-hunter

cd /opt/freelance-hunter
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
# Core dependencies
pip install flask flask-cors requests beautifulsoup4 lxml

# Google Sheets
pip install google-api-python-client google-auth

# Discord
pip install discord.py

# Additional
pip install schedule python-dotenv playwright
pip install aiohttp asyncio
```

### 4. Install Playwright

```bash
playwright install chromium
playwright install-deps
```

### 5. Create Directory Structure

```bash
mkdir -p /opt/freelance-hunter/{config,data/{jobs,proposals,notifications,archive},logs,scraper,agents,scheduler,sheets,dashboard,discord}
mkdir -p /opt/freelance-hunter/data/agents
```

### 6. Configuration Files

Create `/opt/freelance-hunter/.env`:

```bash
# API Configuration
export FLASK_APP=dashboard/main.py
export FLASK_ENV=production

# Ollama
export OLLAMA_HOST=http://localhost:11434

# Google Sheets
export FREELANCE_SPREADSHEET_ID=your_spreadsheet_id_here
export GOOGLE_APPLICATION_CREDENTIALS=/opt/freelance-hunter/config/sheets-credentials.json

# Discord (optional)
export DISCORD_BOT_TOKEN=your_discord_bot_token

# Telegram (optional)
export TELEGRAM_BOT_TOKEN=your_telegram_token
export TELEGRAM_CHAT_IDS=your_chat_id

# Email (optional)
export SMTP_HOST=smtp.gmail.com
export SMTP_PORT=587
export SMTP_USER=your_email@gmail.com
export SMTP_PASSWORD=your_app_password
export FROM_EMAIL=alerts@freelance-hunter.local
export TO_EMAILS=you@example.com
```

Create `/opt/freelance-hunter/config/profile.py`:

```python
# Your skills profile
SKILLS_PROFILE = {
    "primary_skills": [
        "Python", "JavaScript", "React", "Node.js",
        "CUDA", "TensorRT", "Deep Learning",
        "Docker", "Kubernetes", "AWS"
    ],
    "secondary_skills": [
        "PostgreSQL", "MongoDB", "Redis",
        "GraphQL", "REST APIs", "FastAPI"
    ],
    "languages": {
        "English": "fluent",
        "Spanish": "native"
    },
    "experience_years": 8,
    "hourly_rate_min": 50,
    "hourly_rate_max": 150,
    "fixed_min": 500,
    "fixed_max": 15000,
    "preferences": {
        "remote_only": True,
        "escrow_required": True,
        "payment_verified": True,
        "min_client_rating": 4.0,
        "max_proposals": 20,
        "avoid_platforms": []
    }
}
```

Create `/opt/freelance-hunter/config/templates.py`:

```python
# Proposal templates
PROPOSAL_TEMPLATES = {
    "hourly": {
        "subject": "Expert {skill} Developer for {job_title}",
        "template": "Your template here..."
    },
    "fixed": {
        "subject": "Professional {job_title}",
        "template": "Your template here..."
    }
}
```

### 7. Ollama Models

Ensure these models are installed:

```bash
# Pull required models
ollama pull qwen2.5-coder:14b
ollama pull llama3.2:3b
ollama pull deepseek-r1:8b
ollama pull glm-4.7-flash:latest

# For embeddings
ollama pull nomic-embed-text-v2-moe:latest
```

### 8. Google Sheets Setup

1. Create Google Cloud project
2. Enable Sheets and Drive APIs
3. Create service account
4. Download credentials JSON
5. Save as `/opt/freelance-hunter/config/sheets-credentials.json`
6. Create spreadsheet and share with service account
7. Copy spreadsheet ID to `.env`

### 9. Create Startup Scripts

Create `/opt/freelance-hunter/start.sh`:

```bash
#!/bin/bash
cd /opt/freelance-hunter
source venv/bin/activate
source .env

# Start API/Dashboard (runs on port 8096)
python dashboard/main.py > logs/dashboard.log 2>&1 &

# Start scheduler
python scheduler/main.py > logs/scheduler.log 2>&1 &

# Start Discord bot (optional)
python discord/bot.py > logs/discord.log 2>&1 &

echo "Freelance Hunter started"
```

Create `/opt/freelance-hunter/stop.sh`:

```bash
#!/bin/bash
pkill -f "freelance-hunter"
pkill -f "dashboard/main.py"
pkill -f "scheduler/main.py"
pkill -f "discord/bot.py"
echo "Freelance Hunter stopped"
```

```bash
chmod +x /opt/freelance-hunter/*.sh
```

### 10. Systemd Service

Create `/etc/systemd/system/freelance-hunter.service`:

```ini
[Unit]
Description=Freelance Hunter - AI Job Discovery
After=network.target ollama.service

[Service]
Type=simple
User=sergiok
WorkingDirectory=/opt/freelance-hunter
Environment=PATH=/opt/freelance-hunter/venv/bin:/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ExecStart=/opt/freelance-hunter/start.sh
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable freelance-hunter
sudo systemctl start freelance-hunter
```

## Verification

### Check Services

```bash
# Check if dashboard is running
curl http://localhost:8096/api/stats

# Check if scheduler is running
tail -f /opt/freelance-hunter/logs/scheduler.log

# Check agents
curl http://localhost:8096/api/agents
```

### Expected Output

```json
{
  "cycle": 10,
  "total_jobs": 150,
  "total_matches": 45,
  "total_proposals": 12,
  "platform_counts": {
    "upwork": 50,
    "remoteok": 35,
    "freelancer": 30,
    "weworkremotely": 25,
    "linkedin": 10
  }
}
```

## Access

| Service | URL |
|---------|-----|
| Dashboard | http://jetson:8096 |
| API | http://jetson:8096/api/ |
| Jobs | http://jetson:8096/api/jobs |
| Hot Jobs | http://jetson:8096/api/hot |
| Stats | http://jetson:8096/api/stats |

## Nginx Proxy (Optional)

```nginx
server {
    listen 8096;
    server_name jetson;

    location / {
        proxy_pass http://127.0.0.1:8096;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Troubleshooting

### No jobs scraped

```bash
# Check logs
tail -f /opt/freelance-hunter/logs/scheduler.log

# Test scraping manually
cd /opt/freelance-hunter
source venv/bin/activate
python -c "
from scraper.main import ScraperOrchestrator
o = ScraperOrchestrator()
jobs = o.scrape_all()
print(f'Found {len(jobs)} jobs')
"
```

### Google Sheets errors

```bash
# Verify credentials
python -c "
from google.oauth2 import service_account
creds = service_account.Credentials.from_service_account_file(
    '/opt/freelance-hunter/config/sheets-credentials.json'
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

### Discord bot not responding

```bash
# Check bot logs
tail -f /opt/freelance-hunter/logs/discord.log

# Test bot token
python -c "
import os
import discord
print('Token:', os.environ.get('DISCORD_BOT_TOKEN', 'Not set'))
"
```

## Maintenance

### Backup Data

```bash
# Backup to external drive
rsync -av /opt/freelance-hunter/data/ /backup/freelance-data/
```

### Clean Old Jobs

```bash
# Remove data older than 30 days
find /opt/freelance-hunter/data -type f -mtime +30 -delete
```

### Update Models

```bash
# Update Ollama models
ollama pull qwen2.5-coder:14b
ollama pull llama3.2:3b
ollama pull deepseek-r1:8b
```

## Usage

### Add Job Manually

```bash
curl -X POST http://localhost:8096/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"title": "Python Developer", "platform": "upwork", "budget": "$1000"}'
```

### Force Scrape

```bash
curl -X POST http://localhost:8096/api/scheduler/run \
  -H "Content-Type: application/json" \
  -d '{"task": "scrape"}'
```

### Generate Proposal

```bash
curl -X POST http://localhost:8096/api/proposals/generate \
  -H "Content-Type: application/json" \
  -d '{"job_id": "JOB001", "match": {"score": 0.8}}'
```

### Sync Sheets

```bash
curl -X POST http://localhost:8096/sheets/sync
```

## Security

- Keep `sheets-credentials.json` private
- Use environment variables for secrets
- Restrict network access to local network
- Regularly update dependencies
- Don't commit `.env` file

## Monitoring

```bash
# Watch stats
watch -n 5 'curl -s http://localhost:8096/api/stats | python -m json.tool'

# Check disk usage
df -h /opt/freelance-hunter

# Check memory
free -h
```

## Summary

| Component | Port | Status |
|-----------|------|--------|
| Dashboard | 8096 | Required |
| API | 8096 | Required |
| Scheduler | Background | Required |
| Discord Bot | N/A | Optional |
| Ollama | 11434 | Required |
| Sheets | API | Required |

## Quick Start

```bash
# One-line start
cd /opt/freelance-hunter && source venv/bin/activate && source .env && python dashboard/main.py & python scheduler/main.py

# Access dashboard
# Open http://jetson:8096 in browser

# Use Discord commands (if configured)
# !status - Check status
# !hot - See hot jobs
# !scrape - Force scrape
```

---

## Complete File Structure

```
/opt/freelance-hunter/
├── .env                          # Environment variables
├── config/
│   ├── profile.py               # Skills profile
│   ├── templates.py             # Proposal templates
│   ├── platforms.py             # Platform configs
│   ├── notifications.py         # Notification settings
│   └── sheets-credentials.json  # Google credentials
├── data/
│   ├── jobs/                    # Scraped jobs
│   ├── proposals/              # Generated proposals
│   ├── notifications/          # Alert logs
│   └── archive/                # Historical data
├── scraper/
│   └── main.py                 # Scraper orchestrator
├── agents/
│   └── main.py                 # Agent system
├── scheduler/
│   └── main.py                 # 5-min scheduler
├── dashboard/
│   └── main.py                 # Web dashboard
├── discord/
│   └── bot.py                  # Discord bot
├── sheets/
│   └── main.py                 # Sheets integration
└── logs/                       # Application logs
```

---

## 🎉 Congratulations!

Freelance Hunter is now installed and running. The platform will:

1. **Scrape 10+ freelance platforms** every 5 minutes
2. **Match jobs** to your skills using AI
3. **Generate proposals** automatically
4. **Send alerts** via Discord/Telegram/Email
5. **Track everything** in Google Sheets
6. **Control via Discord** commands

Happy hunting! 🎯
