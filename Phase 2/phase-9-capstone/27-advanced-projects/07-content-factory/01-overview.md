# INNOVALABS Literature Factory

## Project Overview

The INNOVALABS Literature Factory is an autonomous AI-powered storytelling system that generates complete short stories using a multi-agent pipeline. It runs entirely on your Jetson AGX Orin and can be accessed remotely from any Windows or Mac computer on your local network.

### What It Does

1. **Scout** - Extracts trending topics from Google Trends
2. **Strategist** - Uses AI to select a theme and create a moral lesson
3. **Architect** - Designs a 12-step story blueprint
4. **Writer** - Generates the complete story using Qwen3.5-27B
5. **Editor** - Polishes the story (grammar, spelling, formatting)

### Features

- **Fully Autonomous**: Runs on a 6-hour schedule via n8n
- **Multi-Agent Pipeline**: 5 specialized AI agents working together
- **Google Sheets Integration**: Queue management and tracking
- **Remote Dashboard**: Monitor and control from Windows/Mac
- **Error Recovery**: Automatic OOM handling and retries

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        INNOVALABS Literature Factory                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                        n8n Workflow Engine                           │  │
│  │                    (Orchestrates the pipeline)                       │  │
│  └─────────────────────────────┬────────────────────────────────────────┘  │
│                                │                                            │
│     ┌──────────┬───────────────┼───────────────┬──────────┐                │
│     ▼          ▼               ▼               ▼          ▼                │
│  ┌──────┐ ┌────────┐    ┌──────────┐   ┌────────┐ ┌────────┐           │
│  │Scout │ │Strate- │    │Architect │   │ Writer │ │ Editor │           │
│  │      │ │  gist  │    │          │   │        │ │        │           │
│  │Python│ │ GLM-4.7│    │DeepSeek  │   │ Qwen3.5│ │Nemotron│           │
│  │Script│ │ Flash  │    │   R1     │   │  27B   │ │  3-nano│           │
│  └──────┘ └────────┘    └──────────┘   └────────┘ └────────┘           │
│     │          │              │             │           │                  │
│     └──────────┴──────────────┴─────────────┴───────────┘                  │
│                                    │                                        │
│                           ┌────────▼────────┐                               │
│                           │  Google Sheets   │                               │
│                           │  (Queue + State) │                               │
│                           └──────────────────┘                               │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                     Dashboard (Port 8080)                           │  │
│  │    CPU │ RAM │ GPU │ Stories │ Controls │ Logs                       │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Device | Jetson AGX Orin 64GB | Jetson AGX Orin 64GB |
| RAM | 32GB | 64GB |
| Storage | 100GB free | 256GB NVMe |
| CUDA | 12.2+ | 12.6 |

### Software

- Ubuntu 22.04 LTS (aarch64)
- JetPack 6.2+
- Docker + NVIDIA Container Toolkit
- Ollama
- llama.cpp (compiled with CUDA)
- Node.js 20 + n8n
- Python 3.10+

### Models Required

| Model | Purpose | Size | Source |
|-------|---------|------|--------|
| glm-4.7-flash | Strategist | ~3 GB | Ollama |
| deepseek-r1:8b | Architect | ~5 GB | Ollama |
| nemotron-3-nano | Editor | ~3 GB | Ollama |
| Qwen3.5-27B-Q4 | Writer | ~16 GB | GGUF |

## Installation

### Step 1: System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install base dependencies
sudo apt install -y \
  build-essential cmake git curl wget unzip jq htop \
  tmux tree openssl ca-certificates gnupg lsb-release \
  software-properties-common apt-transport-https

# Configure timezone
sudo timedatectl set-timezone America/Bogota
```

### Step 2: Configure Performance Mode

```bash
# Set MAXN mode (maximum performance)
sudo nvpmodel -m 0

# Lock GPU/CPU clocks
sudo jetson_clocks

# Verify
sudo nvpmodel -q
# Expected: 0 (MAXN)
```

### Step 3: Install Docker and NVIDIA Container Toolkit

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

# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Step 4: Install Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Configure for sequential model loading
sudo mkdir -p /etc/systemd/system/ollama.service.d/

cat << 'EOF' | sudo tee /etc/systemd/system/ollama.service.d/override.conf
[Service]
Environment="OLLAMA_MAX_LOADED_MODELS=1"
Environment="OLLAMA_KEEP_ALIVE=2m"
Environment="OLLAMA_HOST=0.0.0.0:11434"
EOF

sudo systemctl daemon-reload
sudo systemctl restart ollama
```

### Step 5: Install llama.cpp with CUDA

```bash
# Clone and build
cd ~
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp

cmake -B build \
  -DGGML_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES="87" \
  -DCMAKE_BUILD_TYPE=Release \
  -DGGML_CUDA_F16=ON

cmake --build build --config Release -j$(nproc)

# Install
sudo cp build/bin/llama-cli /usr/local/bin/
sudo chmod +x /usr/local/bin/llama-cli
```

### Step 6: Download AI Models

```bash
# Ollama models
ollama pull glm-4.7-flash:latest
ollama pull deepseek-r1:8b
ollama pull nemotron-3-nano:latest

# GGUF model for Writer
pip install huggingface-hub
mkdir -p ~/.cache/llama.cpp

huggingface-cli download \
  unsloth/Qwen3.5-27B-GGUF \
  Qwen3.5-27B-UD-Q4_K_XL.gguf \
  --local-dir ~/.cache/llama.cpp \
  --local-dir-use-symlinks False

# Rename for workflow
cd ~/.cache/llama.cpp
mv Qwen3.5-27B-UD-Q4_K_XL.gguf \
   unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf
```

### Step 7: Install Python Dependencies

```bash
python3 -m venv /opt/innovalabs/venv
source /opt/innovalabs/venv/bin/activate

pip install --upgrade pip
pip install pytrends==4.9.2 requests pandas

deactivate
```

### Step 8: Install Node.js and n8n

```bash
# Install Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install n8n
npm install -g n8n
```

### Step 9: Create Directory Structure

```bash
sudo mkdir -p /opt/innovalabs/{scripts,config,logs}
sudo mkdir -p /var/opt/innovalabs/historias
sudo mkdir -p /tmp/innovalabs

sudo chown -R $USER:$USER /opt/innovalabs /var/opt/innovalabs
```

### Step 10: Configure n8n Service

```bash
cat << 'EOF' | sudo tee /etc/systemd/system/n8n.service
[Unit]
Description=INNOVALABS n8n Workflow Orchestrator
After=network.target ollama.service docker.service

[Service]
Type=simple
User=sergiok
WorkingDirectory=/opt/innovalabs

Environment="N8N_PORT=5678"
Environment="N8N_PROTOCOL=http"
Environment="GENERIC_TIMEZONE=America/Bogota"
Environment="N8N_DEFAULT_EXECUTION_TIMEOUT=1800"
Environment="N8N_MAX_EXECUTION_TIMEOUT=3600"
Environment="N8N_BASIC_AUTH_ACTIVE=true"
Environment="N8N_BASIC_AUTH_USER=admin"
Environment="N8N_BASIC_AUTH_PASSWORD=CHANGE_THIS_PASSWORD"
Environment="PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/cuda/bin"

ExecStart=/usr/bin/n8n start
Restart=always
RestartSec=10
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable n8n
sudo systemctl start n8n
```

## Google Sheets Setup

### Create Spreadsheet

1. Create a new Google Spreadsheet
2. Rename first sheet to: `Queue_Historias`
3. Add headers in row 1:

```
ID | Fecha | Tema | Contexto | Estado | Path_Archivo | Moraleja | Blueprint_JSON | Error_Log
```

4. Copy the Spreadsheet ID from the URL

### Configure OAuth2 in n8n

1. Go to https://console.cloud.google.com/
2. Create project: `INNOVALABS-Factory`
3. Enable: Google Sheets API + Google Drive API
4. Create OAuth2 credentials (Web application)
5. Add redirect URIs:
   - `http://localhost:5678/rest/oauth2-credential/callback`
   - `http://<JETSON_IP>:5678/rest/oauth2-credential/callback`
6. In n8n: Settings → Credentials → Add → Google Sheets OAuth2

## Workflow Configuration

### Import Workflow

1. Open n8n: `http://<JETSON_IP>:5678`
2. Workflows → Import from File
3. Select `INNOVALABS_Literature_Factory_v1.0.json`

### Update Spreadsheet ID

Replace all 6 occurrences of the spreadsheet ID in the workflow nodes:
- 📋 Sheets — Append Queue
- 📖 Sheets — Leer PENDING
- 🔒 Sheets — Lock PROCESSING
- ✅ Sheets — COMPLETED
- ❌ Sheets — FAILED
- Error Trigger nodes

### Configure Settings

In workflow Settings:
- **Error Workflow**: Select error sub-workflow
- **Timezone**: America/Bogota
- **Max Concurrency**: 1 (CRITICAL - prevents VRAM collisions)

## Dashboard Installation

### Install Dependencies

```bash
source /opt/innovalabs/venv/bin/activate
pip install fastapi==0.115.0 uvicorn[standard] pydantic
deactivate
```

### Create Dashboard Service

```bash
sudo mkdir -p /opt/innovalabs/dashboard/templates

# Copy files from graduation-project
cp dashboard_server.py /opt/innovalabs/dashboard/
cp dashboard_templates_*.html /opt/innovalabs/dashboard/templates/

cat << 'EOF' | sudo tee /etc/systemd/system/innovalabs-dashboard.service
[Unit]
Description=INNOVALABS Dashboard
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/opt/innovalabs/dashboard
ExecStart=/opt/innovalabs/venv/bin/python server.py --port 8080
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable innovalabs-dashboard
sudo systemctl start innovalabs-dashboard
```

## Access from Windows/Mac

### Option 1: Direct IP Access

```
http://<JETSON_IP>:5678    # n8n
http://<JETSON_IP>:8080    # Dashboard
```

### Option 2: SSH Tunnel

```bash
# From Windows/Mac terminal
ssh -L 5678:localhost:5678 -L 8080:localhost:8080 sergiok@<JETSON_IP>
```

Then access:
- n8n: http://localhost:5678
- Dashboard: http://localhost:8080

## Pipeline Parameters

### Per-Agent Settings

| Agent | Model | RAM | GPU | Temp |
|-------|-------|-----|-----|------|
| Scout | pytrends | <100MB | No | - |
| Strategist | glm-4.7-flash | ~4GB | Yes | 0.3 |
| Architect | deepseek-r1:8b | ~6GB | Yes | 0.5 |
| Writer | Qwen3.5-27B Q4 | ~18GB | Yes | 0.8 |
| Editor | nemotron-3-nano | ~5GB | Yes | 0.3 |

### Writer Critical Settings

| Parameter | Value | Justification |
|-----------|-------|---------------|
| -m | Qwen3.5-27B-Q4.gguf | Fits in 64GB |
| -ngl 999 | All layers | Full GPU offload |
| -c 8192 | Context window | Long stories |
| -n 8000 | Max tokens | Story length |
| --temp 0.8 | High creativity | Literary prose |
| --repeat-penalty 1.1 | Anti-repetition | Avoid loops |
| /no_think | Injected in prompt | Disable CoT |

### Resource Estimates

| Phase | Duration | RAM Peak | GPU |
|-------|----------|----------|-----|
| Scout | 10-30s | <100MB | No |
| Strategist | 30-120s | ~4GB | Yes |
| Architect | 60-180s | ~6GB | Yes |
| Writer | 15-30min | ~18GB | Yes |
| Editor | 60-180s | ~5GB | Yes |
| **Total** | **~20-35min** | **18GB** | - |

## Testing

### Manual Execution

1. Open n8n → Select workflow → Click "Execute Workflow"
2. Monitor each node execution
3. Check Google Sheets for status updates
4. Verify .md file in `/var/opt/innovalabs/historias/`

### API Testing

```bash
# Check Ollama
curl http://localhost:11434/api/tags

# Test models
curl -s http://localhost:11434/api/generate -d '{
  "model": "glm-4.7-flash:latest",
  "prompt": "Test",
  "stream": false
}'

# Check n8n
curl http://localhost:5678/healthz
```

## Troubleshooting

### Out of Memory (OOM)

The workflow includes automatic OOM recovery:
1. Status updated to `FAILED_OOM` in Google Sheets
2. Docker restarts Ollama
3. Item stays in queue for retry

### Manual Recovery

```bash
# Restart Ollama
docker restart ollama

# Clear VRAM
sudo systemctl restart ollama

# Check logs
journalctl -u n8n -f --no-pager
```

## Next Steps

- [02-scraper](./02-scraper.md) - Detailed Scout configuration
- [03-agents](./03-agents.md) - AI agent customization
- [04-summary](./04-summary.md) - Output format configuration
- [05-deployment](./05-deployment.md) - Production deployment
