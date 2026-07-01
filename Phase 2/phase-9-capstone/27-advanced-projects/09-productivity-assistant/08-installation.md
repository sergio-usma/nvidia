# AI Office - Complete Installation Guide

## System Requirements

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Device | Jetson AGX Orin 64GB | Jetson AGX Orin 64GB |
| RAM | 32GB | 64GB |
| Storage | 128GB | 256GB NVMe |

### Software

- Ubuntu 22.04 LTS (aarch64)
- JetPack 6.2+
- Ollama
- Node.js 20
- Python 3.10+

## Installation Steps

### Step 1: System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y \
  python3-pip python3-venv git curl wget

# Performance mode
sudo nvpmodel -m 0
sudo jetson_clocks
```

### Step 2: Create Project Directory

```bash
mkdir -p /opt/ai-office/{api,agents,scheduler,discord,dashboard,data,logs}
cd /opt/ai-office

# Create virtual environment
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Python Dependencies

```bash
pip install --upgrade pip
pip install flask requests gunicorn
```

### Step 4: Install Ollama Models

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull qwen2.5-coder:14b
ollama pull deepseek-r1:8b
ollama pull llama3.2:3b
ollama pull glm-4.7-flash:latest
```

### Step 5: Install Node.js

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### Step 6: Install n8n (Optional)

```bash
npm install -g n8n
```

## Configuration

### Create Configuration File

```bash
cat > /opt/ai-office/config.py << 'EOF'
"""AI Office Configuration"""

CONFIG = {
    # API Server
    "api_host": "0.0.0.0",
    "api_port": 9001,
    
    # Data directories
    "data_dir": "/opt/ai-office/data",
    "logs_dir": "/opt/ai-office/logs",
    
    # Ollama
    "ollama_host": "http://localhost:11434",
    
    # Scheduler
    "poll_interval": 900,  # 15 minutes
    
    # Discord (optional)
    "discord_bot_token": "",
    
    # Agent models
    "models": {
        "lead": "qwen2.5-coder:14b",
        "frontend": "qwen2.5-coder:14b",
        "backend": "deepseek-r1:8b",
        "qa": "qwen2.5-coder:14b",
        "content": "llama3.2:3b",
        "scheduler": "glm-4.7-flash:latest"
    },
    
    # Token costs (per 1K tokens)
    "token_costs": {
        "qwen2.5-coder:14b": 0.10,
        "deepseek-r1:8b": 0.10,
        "llama3.2:3b": 0.08,
        "glm-4.7-flash:latest": 0.05
    }
}
EOF
```

## Running the System

### 1. Start the API Server

```bash
cd /opt/ai-office
source venv/bin/activate
python api/server.py &
```

### 2. Start the Scheduler

```bash
cd /opt/ai-office
source venv/bin/activate
python scheduler/main.py &
```

### 3. Start the Dashboard

```bash
cd /opt/ai-office
source venv/bin/activate
python dashboard/server.py &
```

## Service Configuration

### Create Systemd Services

```bash
# API Server
sudo tee /etc/systemd/system/ai-office-api.service << 'EOF'
[Unit]
Description=AI Office API Server
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/opt/ai-office
ExecStart=/opt/ai-office/venv/bin/python api/server.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Scheduler
sudo tee /etc/systemd/system/ai-office-scheduler.service << 'EOF'
[Unit]
Description=AI Office Scheduler
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/opt/ai-office
ExecStart=/opt/ai-office/venv/bin/python scheduler/main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Dashboard
sudo tee /etc/systemd/system/ai-office-dashboard.service << 'EOF'
[Unit]
Description=AI Office Dashboard
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/opt/ai-office
ExecStart=/opt/ai-office/venv/bin/python dashboard/server.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable all
sudo systemctl daemon-reload
sudo systemctl enable ai-office-api ai-office-scheduler ai-office-dashboard
sudo systemctl start ai-office-api ai-office-scheduler ai-office-dashboard
```

## Access URLs

| Service | Port | URL |
|---------|------|-----|
| Dashboard | 9000 | http://<IP>:9000 |
| API | 9001 | http://<IP>:9001 |
| n8n | 5678 | http://<IP>:5678 |

## Testing

### Test API

```bash
# Health check
curl http://localhost:9001/api/health

# Get status
curl http://localhost:9001/api/status

# Get stats
curl http://localhost:9001/api/stats

# Create request
curl -X POST http://localhost:9001/api/requests \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test feature",
    "description": "This is a test",
    "type": "feature",
    "priority": 3
  }'
```

### Test Dashboard

```
http://localhost:9000
```

## Creating Work Requests

### Via API

```python
import requests

# Create request
requests.post("http://localhost:9001/api/requests", json={
    "title": "Add user profile page",
    "description": "Create a user profile page with avatar, bio, and activity",
    "type": "feature",
    "priority": 2
})
```

### Via Discord Bot

```
/request "Add user profile" "Create profile page" feature
```

## Discord Setup (Optional)

### Create Bot

1. Go to https://discord.com/developers/applications
2. Create application → Bot
3. Get token
4. Enable Message Content Intent

### Configure

```bash
# Set token
export DISCORD_BOT_TOKEN=your_token_here

# Start bot
cd /opt/ai-office
source venv/bin/activate
python discord/bot.py
```

### Discord Commands

| Command | Description |
|---------|-------------|
| `/status` | Show office status |
| `/request` | Create new request |
| `/queue` | Show pending requests |
| `/activity` | Show recent activity |
| `/stats` | Show statistics |

## Monitoring

```bash
# Check services
sudo systemctl status ai-office-*

# View logs
journalctl -u ai-office-api -f
journalctl -u ai-office-scheduler -f
journalctl -u ai-office-dashboard -f

# Resource usage
tegrastats --interval 5000
```

## Usage Example

### 1. Create a Work Request

```bash
curl -X POST http://localhost:9001/api/requests \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Build REST API",
    "description": "Create a REST API for user management with CRUD operations",
    "type": "feature",
    "priority": 2
  }'
```

### 2. Watch Progress

- Open dashboard: http://localhost:9000
- See agents working in real-time
- Monitor activity log

### 3. Get Results

```bash
# List completed requests
curl http://localhost:9001/api/requests | jq '.[] | select(.status=="completed")'
```

## Troubleshooting

### Agent Not Responding

```bash
# Check Ollama
curl http://localhost:11434/api/tags

# Check agent logs
tail -f /opt/ai-office/logs/*.log
```

### Queue Not Processing

```bash
# Check scheduler
journalctl -u ai-office-scheduler -f

# Manual trigger
curl http://localhost:9001/api/scheduler/run
```

### High Memory Usage

```bash
# Check GPU
tegrastats

# Restart services
sudo systemctl restart ai-office-*
```
