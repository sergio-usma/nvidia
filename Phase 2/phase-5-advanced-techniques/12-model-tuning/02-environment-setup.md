# Environment Setup for Fine-Tuning

## Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | Jetson AGX Orin 32GB | Jetson AGX Orin 64GB |
| RAM | 32GB | 64GB |
| Storage | 128GB | 512GB NVMe |
| VRAM | 16GB | 32GB+ |

## Software Requirements

- Ubuntu 22.04.5 LTS aarch64
- JetPack 6.2.2
- CUDA 12.6
- Python 3.10+

## Verify Your Environment

```bash
# Check CUDA version
nvcc --version

# Check GPU
nvidia-smi

# Check Python
python3 --version

# Check JetPack
cat /etc/nv_tegra_release
```

## Install Python Dependencies

### Core Dependencies

```bash
# Update package list
sudo apt update && sudo apt upgrade -y

# Install Python if not present
sudo apt install -y python3 python3-pip python3-venv

# Upgrade pip
pip3 install --upgrade pip
```

### PyTorch with CUDA Support

```bash
# Install PyTorch for CUDA 12.x
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Verify PyTorch CUDA
python3 -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda}')"
```

### Transformers and Related Libraries

```bash
# Install main libraries
pip3 install \
    transformers \
    datasets \
    peft \
    accelerate \
    bitsandbytes \
    trl \
    scipy \
    scikit-learn
```

### Unsloth (Recommended for Jetson)

```bash
# Install Unsloth
pip3 install unsloth

# Verify installation
python3 -c "import unsloth; print('Unsloth installed successfully')"
```

### Additional Utilities

```bash
# For data processing
pip3 install pandas numpy tqdm

# For model evaluation
pip3 install lm-eval

# For visualization
pip3 install matplotlib seaborn
```

## Performance Optimization

### Enable MAXN Mode

```bash
# Maximum performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Verify
jtop
```

### Set CUDA Environment Variables

```bash
# Add to ~/.bashrc
export CUDA_HOME=/usr/local/cuda
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

# Reload
source ~/.bashrc
```

### Swap Space (if needed)

```bash
# Create 32GB swap file
sudo fallocate -l 32G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Make permanent
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## Verify Installation

```bash
# Test all imports
python3 << 'EOF'
import torch
print(f"PyTorch: {torch.__version__}")
print(f"CUDA: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")

try:
    import transformers
    print(f"Transformers: {transformers.__version__}")
except ImportError:
    print("Transformers: Not installed")

try:
    import unsloth
    print(f"Unsloth: Installed")
except ImportError:
    print("Unsloth: Not installed")

try:
    import peft
    print(f"PEFT: {peft.__version__}")
except ImportError:
    print("PEFT: Not installed")
EOF
```

## Docker Alternative

If you prefer Docker:

```bash
# Pull PyTorch Docker image
docker pull pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

# Run with GPU access
docker run --gpus all -it --rm \
    -v $(pwd):/workspace \
    pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime \
    bash
```

## Directory Structure

```bash
# Create fine-tuning directory
mkdir -p ~/finetune
cd ~/finetune

# Create subdirectories
mkdir -p {data,models,output,logs}

# Structure
~/finetune/
├── data/           # Training datasets
├── models/        # Base models
├── output/        # Fine-tuned models
└── logs/          # Training logs
```

## Common Issues

### Out of Memory

```bash
# Check available memory
free -h

# Check GPU memory
tegrastats | grep RAM

# Reduce batch size in training script
```

### CUDA Not Found

```bash
# Verify CUDA installation
ls -la /usr/local/cuda

# Reinstall PyTorch with correct CUDA version
pip3 uninstall torch
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### Import Errors

```bash
# Upgrade all packages
pip3 install --upgrade transformers datasets peft accelerate

# Install missing dependencies
pip3 install sentencepiece protobuf
```

## Next Steps

Now proceed to [Alpaca-Guanaco Format](./03-alpaca-guanaco-format.md) to prepare your training data.
