# ComfyUI Setup on Jetson

## Installation

### Prerequisites

```bash
# Install dependencies
sudo apt update
sudo apt install -y python3.10-venv python3-pip libgl1-mesa-glx libglib2.0-0

# Create virtual environment
python3 -m venv ~/comfyui_env
source ~/comfyui_env/bin/activate
```

### Clone ComfyUI

```bash
cd ~
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# Install requirements
pip install -r requirements.txt
```

## Running ComfyUI

```bash
# Activate environment
source ~/comfyui_env/bin/activate

# Run with CPU (Jetson)
python3 main.py --cpu

# Run with CUDA
python3 main.py --cuda
```

## Accessing ComfyUI

```bash
# Default: http://localhost:8188
# For remote access
python3 main.py --listen 0.0.0.0 --port 8188
```

## Installing Models

### Stable Diffusion Models

```bash
# Download to models folder
mkdir -p ~/ComfyUI/models/checkpoints
# Copy or link your models
ln -s ~/unsloth/stable-diffusion/*.safetensors ~/ComfyUI/models/checkpoints/
```

### VAE Models

```bash
mkdir -p ~/ComfyUI/models/vae
# Add VAE files
```

### LoRA Models

```bash
mkdir -p ~/ComfyUI/models/loras
# Add LoRA files
```

## Running as Service

```bash
# Create systemd service
sudo tee /etc/systemd/system/comfyui.service << 'EOF'
[Unit]
Description=ComfyUI
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/home/sergiok/ComfyUI
ExecStart=/home/sergiok/comfyui_env/bin/python3 main.py --listen 0.0.0.0 --port 8188
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable comfyui
sudo systemctl start comfyui
```

## API Access

```bash
# Enable API
# Add to command: --enable-api

python3 main.py --listen 0.0.0.0 --port 8188 --enable-api
```

## Next Steps

- [Ollama Integration](./03-ollama-integration.md) - Connect Ollama
- [Workflow Basics](./04-workflow-basics.md) - Create workflows
