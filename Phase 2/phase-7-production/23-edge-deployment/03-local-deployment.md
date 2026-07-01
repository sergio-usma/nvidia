# Local Deployment

Deploy AI services directly on your Jetson AGX Orin for maximum performance and privacy.

## Service Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Jetson AGX Orin                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Ollama    │  │ llama.cpp   │  │  API Server         │ │
│  │  (port 11434)│ │ (GPU mode)  │  │  (FastAPI/Flask)    │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │  Whisper    │  │   Piper     │  │  Web UI             │ │
│  │  (port 8001)│  │  (port 8002)│  │  (Streamlit/Gradio) │ │
│  └─────────────┘  └─────────────┘  └─────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Performance Mode

Always enable max performance before running AI workloads:

```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

Verify:
```bash
sudo nvpmodel -q
jetson_clocks --show
```

### 2. Start Ollama Service

```bash
# Start as background service
ollama serve &

# Or use systemd (recommended)
sudo systemctl enable ollama
sudo systemctl start ollama
```

Verify:
```bash
curl http://localhost:11434/api/tags
```

### 3. Start API Server

```bash
# Using FastAPI
cd ~/ai-api-server
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

## Production Deployment

### Systemd Services

Create `/etc/systemd/system/ollama.service`:

```ini
[Unit]
Description=Ollama Service
After=network-online.target
Wants=network-online.target

[Service]
Type=notify
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=10
Environment="PATH=/usr/local/cuda-12/bin:/usr/local/bin:/usr/bin:/bin"
Environment="LD_LIBRARY_PATH=/usr/local/cuda-12/lib64:/usr/lib/aarch64-linux-gnu"

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama
```

### Multiple Service Management

Create `/etc/systemd/system/ai-stack.service`:

```ini
[Unit]
Description=AI Stack Manager
After=network.target

[Service]
Type=simple
User=jetson
WorkingDirectory=/home/jetson/ai-stack
ExecStart=/home/jetson/ai-stack/start.sh
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
```

## Environment Configuration

Create `/home/jetson/ai-stack/.env`:

```bash
# Ollama
OLLAMA_HOST=0.0.0.0:11434
OLLAMA_MODELS=/data/models
OLLAMA_GPU_LAYERS=99

# API Server
API_HOST=0.0.0.0
API_PORT=5000
API_WORKERS=2

# Model Configuration
DEFAULT_MODEL=qwen2.5-coder
EMBEDDING_MODEL=nomic-embed-text
WHISPER_PORT=8001
PIPER_PORT=8002
```

## Startup Script

Create `/home/jetson/ai-stack/start.sh`:

```bash
#!/bin/bash
set -e

echo "Starting AI Stack..."

# Performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Start services
systemctl start ollama
systemctl start whisper-api
systemctl start piper-api

# Wait for services
sleep 5

# Verify
curl -s http://localhost:11434/api/tags > /dev/null && echo "Ollama: OK"
curl -s http://localhost:8001/health > /dev/null && echo "Whisper: OK"
curl -s http://localhost:8002/health > /dev/null && echo "Piper: OK"

echo "AI Stack started successfully"
```

Make executable:

```bash
chmod +x /home/jetson/ai-stack/start.sh
```

## Health Checks

Create `/home/jetson/ai-stack/health.sh`:

```bash
#!/bin/bash

check_service() {
    local name=$1
    local url=$2
    
    if curl -sf "$url" > /dev/null 2>&1; then
        echo "✓ $name"
        return 0
    else
        echo "✗ $name"
        return 1
    fi
}

echo "Checking services..."
check_service "Ollama" "http://localhost:11434/api/tags"
check_service "Whisper API" "http://localhost:8001/health"
check_service "Piper TTS" "http://localhost:8002/health"
check_service "API Server" "http://localhost:5000/health"
```

## Resource Monitoring

Add to startup:

```bash
# Add to /home/jetson/ai-stack/start.sh after services start
tmux new -s monitor -d
tmux send-keys 'htop' C-m
```

Or use systemd timers for health monitoring:

```bash
sudo systemctl enable health-check.timer
sudo systemctl start health-check.timer
```

## Next Steps

- [Offline Deployment](./04-offline-deployment.md) - Run without internet
- [Private Network](./05-private-network.md) - Secure internal network
