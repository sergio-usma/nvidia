# INNOVALABS — Detailed Installation

## System Requirements Verification

### Hardware Check

```bash
# Verify architecture
uname -m
# Expected: aarch64

# Check RAM
free -h
# Expected: ~62GB available

# Check storage
df -h
# Recommended: 100GB+ free
```

### CUDA Verification

```bash
# Check JetPack
dpkg -l | grep nvidia-jetpack

# Check CUDA
nvcc --version
# Expected: 12.6

# Check cuDNN
cat /usr/include/cudnn_version.h | grep CUDNN_MAJOR

# Check TensorRT
dpkg -l | grep tensorrt

# Test GPU
/usr/local/cuda/extras/demo_suite/deviceQuery
```

## Docker Configuration

### Daemon Configuration

```bash
cat << 'EOF' | sudo tee /etc/docker/daemon.json
{
  "default-runtime": "nvidia",
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "args": []
    }
  },
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "50m",
    "max-file": "5"
  }
}
EOF

sudo systemctl restart docker

# Verify
docker info | grep -i runtime
```

### Test GPU in Docker

```bash
docker run --rm --runtime=nvidia \
  nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi
```

## Model Installation Details

### Ollama Models

```bash
# Strategist - Theme and moral generation
ollama pull glm-4.7-flash:latest

# Architect - Story blueprint creation  
ollama pull deepseek-r1:8b

# Editor - Grammar and style correction
ollama pull nemotron-3-nano:latest

# Verify
ollama list
```

### GGUF Model for Writer

```bash
# Install huggingface-hub
pip install huggingface-hub

# Create directory
mkdir -p ~/.cache/llama.cpp

# Download Qwen3.5-27B (Q4 quantization ~16GB)
huggingface-cli download \
  unsloth/Qwen3.5-27B-GGUF \
  Qwen3.5-27B-UD-Q4_K_XL.gguf \
  --local-dir ~/.cache/llama.cpp \
  --local-dir-use-symlinks False

# Rename for workflow compatibility
cd ~/.cache/llama.cpp
mv Qwen3.5-27B-UD-Q4_K_XL.gguf \
   unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf

# Verify
ls -lh ~/.cache/llama.cpp/*.gguf
```

### Test llama-cli

```bash
# Quick test - generates 50 tokens
llama-cli \
  -m ~/.cache/llama.cpp/unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf \
  -ngl 999 \
  -c 512 \
  -n 50 \
  -p "Hello, respond briefly: /no_think" \
  2>/dev/null
```

## Python Environment

### Virtual Environment Setup

```bash
# Create venv
python3 -m venv /opt/innovalabs/venv

# Activate
source /opt/innovalabs/venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install \
  pytrends==4.9.2 \
  requests>=2.28.0 \
  pandas>=1.5.0

# Verify
python3 -c "from pytrends.request import TrendReq; print('OK')"

deactivate
```

### Create Activation Script

```bash
cat << 'EOF' > /opt/innovalabs/scripts/activate_env.sh
#!/bin/bash
source /opt/innovalabs/venv/bin/activate
EOF
chmod +x /opt/innovalabs/scripts/activate_env.sh
```

## n8n Setup

### Service Configuration

```bash
# Generate encryption key
N8N_KEY=$(openssl rand -hex 32)

cat << EOF | sudo tee /etc/systemd/system/n8n.service
[Unit]
Description=INNOVALABS n8n Workflow Orchestrator
After=network.target ollama.service docker.service
Wants=ollama.service

[Service]
Type=simple
User=sergiok
WorkingDirectory=/opt/innovalabs

Environment="N8N_PORT=5678"
Environment="N8N_PROTOCOL=http"
Environment="GENERIC_TIMEZONE=America/Bogota"
Environment="TZ=America/Bogota"
Environment="N8N_DEFAULT_BINARY_DATA_MODE=filesystem"
Environment="N8N_DEFAULT_EXECUTION_TIMEOUT=1800"
Environment="N8N_MAX_EXECUTION_TIMEOUT=3600"
Environment="N8N_BASIC_AUTH_ACTIVE=true"
Environment="N8N_BASIC_AUTH_USER=admin"
Environment="N8N_BASIC_AUTH_PASSWORD=YOUR_SECURE_PASSWORD"
Environment="N8N_ENCRYPTION_KEY=${N8N_KEY}"
Environment="PATH=/usr/local/bin:/usr/bin:/bin:/usr/local/cuda/bin"
Environment="LD_LIBRARY_PATH=/usr/local/cuda/lib64"

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

# Verify
curl -s http://localhost:5678/healthz
```

### Access n8n

Open browser: `http://<JETSON_IP>:5678`

## Google Sheets Integration

### Create Credentials

1. Go to https://console.cloud.google.com/
2. Create project: `INNOVALABS-Factory`
3. Enable APIs:
   - Google Sheets API
   - Google Drive API
4. Credentials → Create OAuth Client ID
5. Application type: Web application
6. Authorized redirect URIs:
   - `http://localhost:5678/rest/oauth2-credential/callback`
   - `http://<JETSON_IP>:5678/rest/oauth2-credential/callback`
7. Download credentials JSON

### Configure in n8n

1. Open n8n → Settings → Credentials
2. Add Credential → Google Sheets OAuth2 API
3. Paste Client ID and Client Secret
4. Click "Connect" and authorize

### Create Spreadsheet

1. Create new Google Spreadsheet
2. Rename sheet to: `Queue_Historias`
3. Add headers (row 1):

| A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|
| ID | Fecha | Tema | Contexto | Estado | Path_Archivo | Moraleja | Blueprint_JSON | Error_Log |

4. Copy spreadsheet ID from URL

## Directory Structure

```bash
/opt/innovalabs/
├── scripts/
│   ├── scout_trends.py        # Trend extraction
│   ├── writer_bridge.sh      # n8n → llama-cli bridge
│   ├── activate_env.sh       # Venv activation
│   └── verify_system.sh      # System verification
├── config/
│   ├── docker-compose.yml    # Docker stack
│   ├── .env                  # Environment variables
│   └── .env.example          # Template
├── logs/                     # Operation logs
├── dashboard/               # Dashboard files
│   ├── server.py
│   └── templates/
└── venv/                    # Python virtual environment

/var/opt/innovalabs/
└── historias/              # Generated stories
    ├── Historia_H-*.md
    └── ...

~/.cache/llama.cpp/
└── unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf
```

## Network Configuration

### Firewall (Optional)

```bash
sudo apt install -y ufw

sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh

# From local network only
sudo ufw allow from 192.168.1.0/24 to any port 5678 comment "n8n"
sudo ufw allow from 192.168.1.0/24 to any port 8080 comment "Dashboard"
sudo ufw allow from 192.168.1.0/24 to any port 11434 comment "Ollama"

sudo ufw enable
```

### Static IP (Optional)

```bash
# Edit netplan config
sudo nano /etc/netplan/01-static-ip.yaml

network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      dhcp4: no
      addresses:
        - 192.168.1.50/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4

sudo netplan apply
```

## Verification Script

```bash
cat << 'EOF' > /opt/innovalabs/scripts/verify_system.sh
#!/bin/bash
echo "═══ INNOVALABS System Verification ═══"

PASS=0; FAIL=0
check() {
  if eval "$2" > /dev/null 2>&1; then
    echo "  ✓ $1"; ((PASS++))
  else
    echo "  ✗ $1"; ((FAIL++))
  fi
}

echo ""
echo "── Hardware ──"
check "aarch64" '[[ "$(uname -m)" == "aarch64" ]]'
check "RAM >= 60GB" '[[ $(free -m | awk "/Mem:/{print \$2}") -ge 60000 ]]'

echo ""
echo "── NVIDIA ──"
check "CUDA 12.6" 'nvcc --version 2>&1 | grep -q "12.6"'
check "Docker NVIDIA" 'docker info 2>/dev/null | grep -q nvidia'

echo ""
echo "── Ollama ──"
check "Ollama API" 'curl -sf http://localhost:11434/api/tags'
check "glm-4.7-flash" 'ollama list 2>/dev/null | grep -q "glm-4.7-flash"'
check "deepseek-r1" 'ollama list 2>/dev/null | grep -q "deepseek-r1"'
check "nemotron-3-nano" 'ollama list 2>/dev/null | grep -q "nemotron-3-nano"'

echo ""
echo "── llama.cpp ──"
check "llama-cli" 'which llama-cli'
check "GGUF model" 'test -f ~/.cache/llama.cpp/unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf'

echo ""
echo "── n8n ──"
check "n8n" 'curl -sf http://localhost:5678/healthz'

echo ""
echo "── Structure ──"
check "Scripts dir" 'test -d /opt/innovalabs/scripts'
check "Stories dir" 'test -d /var/opt/innovalabs/historias'

echo ""
echo "═══════════════════════════════════"
echo "  Result: $PASS passed, $FAIL failed"
echo "═══════════════════════════════════"
EOF

chmod +x /opt/innovalabs/scripts/verify_system.sh
bash /opt/innovalabs/scripts/verify_system.sh
```
