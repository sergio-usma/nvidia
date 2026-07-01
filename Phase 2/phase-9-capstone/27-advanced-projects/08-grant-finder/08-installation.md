# Funding Finder - Complete Installation Guide

## System Requirements

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Device | Jetson AGX Orin 64GB | Jetson AGX Orin 64GB |
| RAM | 32GB | 64GB |
| Storage | 256GB | 512GB NVMe |
| GPU | 16GB VRAM | 32GB (with swap) |

### Software

- Ubuntu 22.04 LTS (aarch64)
- JetPack 6.2+
- Docker + NVIDIA Container Toolkit
- Ollama
- Node.js 20 + n8n
- Python 3.10+

## Installation Steps

### Step 1: System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install base dependencies
sudo apt install -y \
  build-essential cmake git curl wget unzip jq htop \
  tmux tree openssl ca-certificates gnupg lsb-release \
  software-properties-common apt-transport-https \
  python3-pip python3-venv libgl1-mesa-glx libglib2.0-0

# Configure performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Set timezone
sudo timedatectl set-timezone America/Bogota
```

### Step 2: Docker & NVIDIA Toolkit

```bash
# Install Docker
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
newgrp docker

# Install NVIDIA Container Toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | \
  sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Step 3: Python Environment

```bash
# Create project directory
mkdir -p /opt/funding-finder
cd /opt/funding-finder

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip

# Core dependencies
pip install \
  flask requests beautifulsoup4 lxml \
  playwright pypdf2 python-docx openpyxl pandas \
  schedule gspread google-auth google-api-python-client \
  chromadb sentence-transformers \
  pydantic \
  smtplib email-validator

# Install Playwright
playwright install chromium
playwright install-deps
```

### Step 4: Install Scrapling

```bash
pip install scrapling
pip install undetected-chromedriver
```

### Step 5: Ollama Models

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull qwen2.5-coder:14b
ollama pull llama3.2:3b
ollama pull glm-4.7-flash:latest
ollama pull deepseek-r1:8b
ollama pull nomic-embed-text:latest

# Verify
ollama list
```

### Step 6: Node.js & n8n

```bash
# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install n8n
npm install -g n8n
```

### Step 7: Create Directory Structure

```bash
mkdir -p /opt/funding-finder/{api,scraper,agents,dashboard,documents,output,logs,config}
mkdir -p /opt/funding-finder/data/{documents,chroma,opportunities}
```

### Step 8: Google Cloud Setup

1. Create project at https://console.cloud.google.com/
2. Enable APIs:
   - Google Sheets API
   - Google Drive API
3. Create Service Account
4. Download credentials.json to `/opt/funding-finder/config/`
5. Share spreadsheet with service account email

### Step 9: Environment Variables

```bash
# Create .env file
cat > /opt/funding-finder/config/.env << 'EOF'
# Ollama
OLLAMA_HOST=http://localhost:11434

# Google Sheets
GOOGLE_CREDENTIALS=/opt/funding-finder/config/credentials.json
SPREADSHEET_ID=your_spreadsheet_id_here

# Google Drive
DRIVE_ROOT_FOLDER=

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EOF
```

### Step 10: Copy Source Files

```bash
# Copy all Python modules
cp -r api/* /opt/funding-finder/api/
cp -r scraper/* /opt/funding-finder/scraper/
cp -r agents/* /opt/funding-finder/agents/
cp -r dashboard/* /opt/funding-finder/dashboard/

# Make executables
chmod +x /opt/funding-finder/*.py
```

## Service Configuration

### Create Systemd Services

```bash
# Scraper Service
sudo tee /etc/systemd/system/funding-scraper.service << 'EOF'
[Unit]
Description=Funding Finder Scraper
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/opt/funding-finder
ExecStart=/opt/funding-finder/venv/bin/python scraper/main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Sheets API Service
sudo tee /etc/systemd/system/funding-sheets.service << 'EOF'
[Unit]
Description=Funding Finder Sheets API
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/opt/funding-finder
ExecStart=/opt/funding-finder/venv/bin/python api/sheets.py 8081
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Dashboard Service
sudo tee /etc/systemd/system/funding-dashboard.service << 'EOF'
[Unit]
Description=Funding Finder Dashboard
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/opt/funding-finder
ExecStart=/opt/funding-finder/venv/bin/python dashboard/server.py 8090
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable funding-scraper funding-sheets funding-dashboard
sudo systemctl start funding-sheets funding-dashboard
```

## n8n Workflow Setup

### Import Workflow

1. Open n8n: `http://<JETSON_IP>:5678`
2. Create new workflow
3. Add nodes:
   - **Cron**: Every hour
   - **HTTP Request**: GET http://localhost:8081/queue/next
   - **IF**: Check if opportunity exists
   - **Download Documents**: Process documents
   - **Generate Proposal**: Call agent system
   - **Update Status**: POST to sheets API
   - **Deliver**: Email + Drive upload

### Workflow JSON

```json
{
  "name": "Funding Finder Pipeline",
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [{"field": "hours", "hoursInterval": 1}]
        }
      },
      "id": "cron",
      "name": "Cron",
      "type": "n8n-nodes-base.cron",
      "typeVersion": 1
    },
    {
      "parameters": {
        "method": "GET",
        "url": "http://localhost:8081/queue/next"
      },
      "id": "get_next",
      "name": "Get Next Opportunity",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 3
    }
  ],
  "connections": {
    "Cron": {"main": [[{"node": "Get Next Opportunity", "type": "main", "index": 0}]]}
  }
}
```

## Testing

### Test APIs

```bash
# Test sheets API
curl http://localhost:8081/health
curl http://localhost:8081/queue/stats

# Test dashboard
curl http://localhost:8090/api/status
```

### Test Scraper

```bash
source /opt/funding-finder/venv/bin/activate
cd /opt/funding-finder
python scraper/main.py
```

## Access URLs

| Service | Port | URL |
|---------|------|-----|
| Dashboard | 8090 | http://<IP>:8090 |
| Factory | 8090 | http://<IP>:8090/factory |
| Sheets API | 8081 | http://<IP>:8081 |
| n8n | 5678 | http://<IP>:5678 |
| Ollama | 11434 | http://<IP>:11434 |

## Network Access from Windows/Mac

### Option 1: Direct Access

```
http://<JETSON_IP>:8090    # Dashboard
http://<JETSON_IP>:5678   # n8n
```

### Option 2: SSH Tunnel

```bash
ssh -L 8090:localhost:8090 -L 5678:localhost:5678 -L 8081:localhost:8081 sergiok@<JETSON_IP>
```

## Monitoring

```bash
# Check all services
sudo systemctl status funding-*

# View logs
journalctl -u funding-scraper -f
journalctl -u funding-sheets -f
journalctl -u funding-dashboard -f

# Check resources
tegrastats --interval 5000
```

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Scraper fails | Check internet, update selectors |
| Sheets API error | Verify credentials and sharing |
| Email not sent | Check SMTP settings, app password |
| Drive upload fails | Verify service account permissions |
| OOM errors | Reduce concurrent agents, add swap |

### Reset

```bash
# Restart all services
sudo systemctl restart funding-*

# Clear cache
rm -rf /opt/funding-finder/data/chroma/*
rm -rf /opt/funding-finder/logs/*
```
