# Install Essential Tools

A single `apt` run that installs everything you'll need for the entire tutorial — from compiling llama.cpp to running Python AI projects.

---

## Step 1: Update Package Index

```bash
sudo apt update && sudo apt upgrade -y
```

---

## Step 2: Core Development Stack

```bash
sudo apt install -y \
    # Version control
    git git-lfs \
    # Build system
    build-essential cmake ninja-build pkg-config \
    # Python
    python3-pip python3-venv python3-dev \
    # Linear algebra (required by PyTorch, BLAS routines)
    libopenblas-dev liblapack-dev \
    # MPI and OpenMP (for distributed/parallel builds)
    libopenmpi-dev libomp-dev \
    # Audio (Whisper STT, Piper TTS)
    alsa-utils pulseaudio-utils portaudio19-dev libsndfile1-dev \
    # Image processing (OpenCV Python, Pillow)
    libjpeg-dev libpng-dev libtiff-dev libwebp-dev \
    # Video (FFmpeg for Whisper audio processing)
    ffmpeg libavcodec-dev libavformat-dev libswscale-dev \
    # Networking and downloads
    curl wget aria2 \
    # Compression
    unzip zip p7zip-full \
    # System utilities
    htop iotop nvtop tmux \
    # Text editors
    nano vim \
    # Monitoring
    lm-sensors i2c-tools \
    # File sync
    rsync
```

---

## Step 3: Python Package Manager Upgrade

The default pip on Ubuntu 22.04 is outdated. Upgrade it:

```bash
python3 -m pip install --upgrade pip setuptools wheel
```

---

## Step 4: Install jtop (Essential Jetson Dashboard)

```bash
sudo pip3 install jetson-stats
sudo systemctl restart jtop.service 2>/dev/null || sudo systemctl start jtop.service
```

Test it:
```bash
jtop --version
jtop  # opens the interactive dashboard, press q to quit
```

---

## Step 5: Docker (if not already installed)

Docker should be pre-installed on JetPack 6.2.2. Verify:

```bash
docker --version
# Expected: Docker version 24.x.x or later

docker info | grep -E "(Runtime|Runtimes)"
# Expected output includes: nvidia (runtime)
```

If Docker is missing:
```bash
sudo apt install docker.io docker-compose-plugin -y
sudo usermod -aG docker $USER
newgrp docker
```

If the NVIDIA runtime is missing:
```bash
sudo apt install nvidia-container-runtime nvidia-container-toolkit -y
sudo systemctl restart docker
```

Verify GPU access from Docker:
```bash
docker run --rm --runtime nvidia --gpus all ubuntu:22.04 nvidia-smi 2>/dev/null || \
  echo "Note: nvidia-smi not on Jetson — test with: docker run --rm --runtime nvidia dustynv/cuda:12.6-runtime-r36.4.0 nvcc --version"
```

---

## Step 6: Git Configuration

```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
git config --global pull.rebase false

# Enable LFS (needed for HuggingFace repos)
git lfs install
```

---

## Step 7: aria2 Configuration (Fast Model Downloads)

`aria2` downloads large files with multiple connections — much faster than `wget` for model files:

```bash
mkdir -p ~/.config/aria2
cat > ~/.config/aria2/aria2.conf << 'EOF'
# Connections per server
max-connection-per-server=8
# Split file into N parts
split=8
# Minimum split size
min-split-size=5M
# Retry on error
max-tries=5
retry-wait=3
# Download directory
dir=/home/sergiok/models
EOF
```

Usage:
```bash
aria2c -x 8 -s 8 "https://huggingface.co/.../model.gguf"
```

---

## Step 8: Create Project Directory Structure

Set up a clean workspace:

```bash
mkdir -p ~/models          # GGUF and HuggingFace models
mkdir -p ~/projects        # Your code
mkdir -p ~/docker          # Docker Compose files
mkdir -p ~/envs            # Python virtual environments

# If you have an NVMe SSD mounted at /data:
# mkdir -p /data/models
# ln -s /data/models ~/models   # symlink so ~/models works everywhere
```

---

## Verification Checklist

```bash
echo "=== Essential Tools Verification ==="
git --version
cmake --version | head -1
python3 --version
pip3 --version
ffmpeg -version 2>&1 | head -1
docker --version
jtop --version 2>/dev/null || echo "jtop: run 'sudo pip3 install jetson-stats'"
echo "aria2c version: $(aria2c --version | head -1)"
echo "=== All done ==="
```

Expected (approximate):
```
git version 2.34.x
cmake version 3.22.x
Python 3.10.x
pip 24.x
ffmpeg version 4.4.x
Docker version 24.x.x
jtop 4.x.x
aria2 1.36.x
```

---

## Package Reference

| Package | Why you need it |
|---------|----------------|
| `git-lfs` | Required for HuggingFace repos with large files |
| `ffmpeg` | Audio processing for Whisper STT |
| `libopenblas-dev` | BLAS routines — speeds up numpy and PyTorch CPU ops |
| `portaudio19-dev` | Microphone input for voice assistant projects |
| `nvtop` | GPU monitoring (alternative to jtop) |
| `aria2` | Multi-threaded downloads (10× faster than wget for large models) |
| `tmux` | Keep model servers running after SSH disconnect |

---

## Next Steps

- **[Configure Shell](05-shell-configuration.md)** — Production `.bashrc` with all CUDA paths
- **[Network Optimization](06-network-optimization.md)** — Faster downloads for model files
