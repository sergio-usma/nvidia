# Creative Studio - Installation Guide

## Prerequisites

- Jetson AGX Orin with JetPack 6.2
- Python 3.12 (via pyenv)
- Ollama running (for prompt enhancement)
- FAL.ai API key (for cloud generation) OR 64GB RAM for local
- 20GB free storage

## Installation Steps

### 1. Create Project Directory

```bash
sudo mkdir -p /opt/creative-studio
sudo chown $USER:$USER /opt/creative-studio
cd /opt/creative-studio
```

### 2. Setup Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

### 3. Install Dependencies

```bash
pip install flask flask-cors requests pillow
pip install ffmpeg-python
pip install python-dotenv pyyaml
```

### 4. Create Directory Structure

```bash
mkdir -p /opt/creative-studio/{config,inputs,outputs,web/templates,logs,modules,workflows}
mkdir -p /opt/creative-studio/outputs/{text2video,image2video,audio2video,multi_scene}
```

### 5. Create Configuration

Create /opt/creative-studio/.env:

```bash
export FAL_API_KEY="your_fal_api_key"
export FLASK_APP=web/main.py
export OUTPUT_DIR=/opt/creative-studio/outputs
export OLLAMA_HOST=http://localhost:11434
```

### 6. FAL.ai Setup (Cloud Option)

1. Go to fal.ai
2. Sign up for account
3. Create API key
4. Add credits
5. Copy key to .env

---

## Option A: Cloud Generation (Recommended)

This uses FAL.ai's API - no local GPU needed:

```bash
# Start server
./start.sh
```

---

## Option B: Local Generation on Jetson Orin

### B1. Install Jetson-Optimized PyTorch

```bash
# DO NOT use standard pip install torch!
# Install Jetson-specific build for JetPack 6.2

pip3 install --no-cache-dir torch torchvision torchaudio \
  --index-url https://pypi.jetson-ai-lab.io/jp6/cu126
```

### B2. Install LTX-2.3 Dependencies

```bash
# Core AI libraries
pip3 install diffusers transformers accelerate sentencepiece

# Optimization
pip3 install optimum-quanto

# Video processing
sudo apt-get install -y ffmpeg
pip3 install av
```

### B3. Configure Unified Memory

Add to ~/.bashrc:

```bash
export JETSON_MAX_ALLOC_PERCENT=90
source ~/.bashrc
```

### B4. Download LTX-2.3 Model

```bash
# Install huggingface-hub
pip3 install huggingface-hub

# Download distilled model (smaller, ~14GB)
huggingface-cli download Lightricks/LTX-Video --local-dir /opt/creative-studio/models/ltx-2.3
```

### B5. Setup ComfyUI (Optional)

```bash
# Create dedicated environment
python3 -m venv comfy-env
source comfy-env/bin/activate

# Install PyTorch
pip3 install --no-cache-dir torch torchvision torchaudio \
  --index-url https://pypi.jetson-ai-lab.io/jp6/cu126

# Clone ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI
pip install -r requirements.txt

# Install LTXVideo nodes
cd custom_nodes
git clone https://github.com/Lightricks/ComfyUI-LTXVideo
cd ComfyUI-LTXVideo
pip install -r requirements.txt
```

### B6. Launch ComfyUI

```bash
# Set memory
export JETSON_MAX_ALLOC_PERCENT=90

# Launch with Orin-optimized flags
python main.py --preview-method auto --use-pytorch-cross-attention --highvram
```

### B7. Performance Tuning

```bash
# MAXN mode (highest performance)
sudo nvpmodel -m 0
sudo jetson_clocks

# Create swap if needed
sudo fallocate -l 20G /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

### 7. Create Startup Script

Create /opt/creative-studio/start.sh:

```bash
#!/bin/bash
cd /opt/creative-studio
source venv/bin/activate
source .env
python web/main.py > logs/server.log 2>&1 &
echo "Creative Studio started on port 8083"
```

```bash
chmod +x /opt/creative-studio/start.sh
```

### 8. Start Server

```bash
./start.sh
```

## Verification

```bash
curl http://localhost:8083/api/health
```

## Access

| Service | URL |
|---------|-----|
| Web Interface | http://jetson:8083 |
| API | http://jetson:8083/api/ |
| ComfyUI | http://jetson:8188 |

## Usage

### Text-to-Video

```bash
curl -X POST http://localhost:8083/api/generate/text2video \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A sunset over mountains", "duration": 5}'
```

### Image-to-Video

```bash
curl -X POST http://localhost:8083/api/generate/image2video \
  -F "image=@/path/to/image.png" \
  -d '{"prompt": "Camera pans left", "duration": 5}'
```

## Troubleshooting

### No video generated

Check FAL.ai key:

```bash
echo $FAL_API_KEY
```

### Ollama connection failed

```bash
curl http://localhost:11434/api/tags
sudo systemctl restart ollama
```

### Out of Memory on Orin

- Use distilled model (ltx-2.3-22b-distilled)
- Use VAE Decode Tiled node in ComfyUI
- Lower resolution: 704x480
- Reduce decode_chunk_size

## File Structure

```
/opt/creative-studio/
├── .env
├── config/
├── inputs/
├── outputs/
├── models/
│   └── ltx-2.3/
├── workflows/
│   ├── ltx-text2video.json
│   └── ltx-image2video.json
├── web/
│   ├── main.py
│   └── templates/
├── modules/
├── logs/
└── start.sh
```

## Features

- Text-to-Video generation
- Image-to-Video animation
- Audio-to-Video visualization
- Web Interface
- REST API
- Local or Cloud generation
- ComfyUI integration

## Integration with Previous Projects

- Project 6: Enhanced Video Studio
- Project 7: Video Proposals
- Project 8: Video Reports
- Project 9: Agent Videos
- Project 10: Tourism Video Reports
- Project 11: Portfolio Videos

## Quick Start

```bash
cd /opt/creative-studio
source venv/bin/activate
source .env
python web/main.py
```

Open http://jetson:8083 in browser.

## LTX-2.3 on Orin Tips

1. Use distilled model for memory efficiency
2. Keep resolution under 704x480 for 64GB Orin
3. Use VAE Decode Tiled to prevent OOM
4. Run in MAXN mode: `sudo nvpmodel -m 0 && sudo jetson_clocks`
5. Create swap space on NVMe SSD

## Congratulations

Creative Studio is now ready to generate amazing videos using LTX-2.3!
