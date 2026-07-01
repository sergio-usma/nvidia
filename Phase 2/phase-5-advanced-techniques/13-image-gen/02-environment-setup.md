# Environment Setup for Image Generation

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | Jetson AGX Orin 32GB | Jetson AGX Orin 64GB |
| RAM | 32GB | 64GB |
| Storage | 256GB | 512GB NVMe |
| VRAM | 8GB | 16GB |

## Software Requirements

- Ubuntu 22.04.5 LTS aarch64
- JetPack 6.2.2
- CUDA 12.6
- Python 3.10+

## Verify CUDA

```bash
# Check CUDA version
nvcc --version

# Check GPU
nvidia-smi

# Check JetPack
cat /etc/nv_tegra_release
```

## Install Dependencies

### Core Packages

```bash
# Update system
sudo apt update && sudo upgrade -y

# Install Python
sudo apt install -y python3 python3-pip python3-venv

# Install CUDA packages
sudo apt install -y cuda-toolkit-12-6
```

### Python Packages

```bash
# Create virtual environment
python3 -m venv img_gen_env
source img_gen_env/bin/activate

# Install PyTorch
pip3 install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Install image generation libraries
pip3 install \
    diffusers \
    transformers \
    accelerate \
    compel \
    invisible-watermark \
    omegaconf \
    pytorch-lightning \
    torchmetrics \
    torchsde \
    scipy \
    safetensors \
    pillow \
    opencv-python \
    numpy

# For model management
pip3 install huggingface-hub
```

### Verify Installation

```python
import torch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'}")
```

## Model Storage

```bash
# Create models directory
mkdir -p ~/models/huggingface
mkdir -p ~/models/diffusers
mkdir -p ~/output/images

# Set environment variable
export HF_HOME=~/models/huggingface
export DIFFUSERS_CACHE=~/models/diffusers
```

## Jetson Optimization

### Enable Performance Mode

```bash
# Maximum performance
sudo nvpmodel -m 0
sudo jetson_clocks

# Verify
jtop
```

### Swap Space (if needed)

```bash
# Create 32GB swap
sudo fallocate -l 32G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Docker Alternative

```bash
# Pull PyTorch with CUDA
docker pull pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

# Run with GPU
docker run --gpus all -it --rm \
    -v $(pwd):/workspace \
    -p 7860:7860 \
    pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime \
    bash
```

## Common Issues

### Out of Memory

```bash
# Check available VRAM
tegrastats | grep RAM

# Reduce batch size
# Use smaller models
# Enable model offload
```

### CUDA Not Found

```bash
# Verify CUDA installation
ls -la /usr/local/cuda

# Set environment
export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH
```

## Directory Structure

```bash
# Create project structure
mkdir -p ~/image-generation/{models,data,output,logs}

# Structure
~/image-generation/
├── models/           # Downloaded models
├── data/            # Input images
├── output/          # Generated images
└── logs/            # Training logs
```

## Next Steps

Proceed to [Interactive Prompt Generator](./03-interactive-prompt.md) to start generating images with customizable parameters.
