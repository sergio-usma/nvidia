# Environment Setup

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Pre-requisites](#pre-requisites)
3. [Install Dependencies](#install-dependencies)
4. [Verify Installation](#verify-installation)

## System Requirements

- **Hardware**: Jetson AGX Orin 64GB
- **OS**: Ubuntu 22.04.5 LTS (aarch64)
- **JetPack**: 6.2.2
- **Python**: 3.10+
- **RAM**: 32GB+ recommended for larger models

## Pre-requisites

### 1. Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Install Python Dependencies

```bash
# Python and pip
sudo apt install -y python3 python3-pip python3-venv

# Development tools
sudo apt install -y build-essential git curl wget

# Required Python packages
pip3 install --upgrade pip
pip3 install requests httpx pyyaml
```

### 3. Install Node.js (for some tools)

```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
```

### 4. Verify CUDA/GPU Access

```bash
# Check CUDA
nvcc --version

# Should show: Cuda compilation tools, release 12.6

# Check GPU
nvidia-smi  # Or tegrastats on Jetson
```

### 5. Ensure Ollama or llama.cpp Running

**Ollama**:
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start service
ollama serve

# Pull coding models
ollama pull qwen2.5-coder:latest
ollama pull codeqwen:latest
```

**llama.cpp**:
```bash
# Clone and build llama.cpp
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
cmake -B build
cmake --build build -j$(nproc)

# Or use pre-built binary
wget https://github.com/ggerganov/llama.cpp/releases/latest/download/llama-cli-aarch64
chmod +x llama-cli-aarch64
```

## Install Dependencies

### For OpenCode

```bash
# Install OpenCode (see dedicated guide for latest method)
curl -sSL https://opencode.ai/install | sh
```

### For Claude Code (API-based)

```bash
# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Or use standalone binary
wget https://github.com/anthropics/claude-code/releases/latest/download/claude-linux-arm64
chmod +x claude-linux-arm64
sudo mv claude-linux-arm64 /usr/local/bin/claude
```

### For Aider (CLI Editor)

```bash
pip3 install aider
```

### For Continue.dev (VS Code)

```bash
# Install Continue VS Code extension
# See VS Code Integration guide
```

## Verify Installation

### Check Python

```bash
python3 --version  # Should be 3.10+
pip3 --version
```

### Check Ollama

```bash
curl http://localhost:11434/api/tags
# Should return list of models
```

### Check llama.cpp

```bash
# Test basic inference
./llama-cli -m ./models/qwen2.5-coder.gguf -p "Hello" -n 10
```

### Check GPU Access

```bash
# For CUDA
python3 -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')"

# For Jetson specific
tegrastats
```

## Performance Optimization

### Enable Max Performance Mode

```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

### Increase Swap (Optional)

```bash
# If running large models, consider adding swap
sudo fallocate -l 16G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Monitor Resources

```bash
# Install htop
sudo apt install -y htop

# Use jtop for Jetson
sudo pip3 install jtop
sudo jtop
```

## Network Configuration

### For Remote Development

If developing remotely:

```bash
# Allow Ollama to listen on network
export OLLAMA_HOST=0.0.0.0:11434

# Or configure firewall
sudo ufw allow 11434/tcp
```

## Next Steps

- [OpenCode Setup](./05-opencode-setup.md)
- [llama.cpp Integration](./07-llama.cpp-integration.md)
- [Ollama Integration](./08-ollama-integration.md)
