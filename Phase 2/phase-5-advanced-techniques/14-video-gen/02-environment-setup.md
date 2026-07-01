# Environment Setup for Video Processing on Jetson AGX Orin

## Table of Contents

1. [System Requirements](#system-requirements)
2. [System Configuration](#system-configuration)
3. [Python Dependencies](#python-dependencies)
4. [Video Processing Libraries](#video-processing-libraries)
5. [AI Model Setup](#ai-model-setup)
6. [Verification](#verification)
7. [Performance Tuning](#performance-tuning)

## System Requirements

### Hardware

- Jetson AGX Orin 64GB (recommended)
- JetPack 6.2.2
- NVMe SSD (recommended for video I/O)
- 16GB+ swap space

### Software

- Ubuntu 22.04 LTS
- Python 3.10+
- CUDA 12.6
- OpenCV 4.8+

## System Configuration

### 1. Enable Maximum Performance

```bash
# Set max performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Verify
sudo nvpmodel -q
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq
```

### 2. Configure Swap Space

```bash
# Check current swap
swapon --show

# Create 16GB swap if needed
sudo fallocate -l 16G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Add to fstab
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### 3. Increase GPU Memory Allocation

```bash
# Edit boot config (if needed)
sudo nano /boot/extlinux/extlinux.conf

# Add to APPEND line:
#tegrademem=16G
```

## Python Dependencies

### 1. Core Dependencies

```bash
# Update package list
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y \
    python3-pip \
    python3-dev \
    python3-numpy \
    libopencv-dev \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libavdevice-dev \
    ffmpeg
```

### 2. Python Packages

```bash
# Core video processing
pip install numpy opencv-python pillow

# Video editing
pip install moviepy

# For AI generation (from Part 17)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126
pip install diffusers transformers accelerate safetensors

# Additional utilities
pip install scipy tqdm imageio imageio-ffmpeg
```

### 3. Verify OpenCV

```bash
# Check OpenCV with video support
python3 -c "import cv2; print(f'OpenCV: {cv2.__version__}'); print(f'Video: {cv2.haveVideoWriter(\"/dev/null\")}')"
```

## Video Processing Libraries

### OpenCV

The core library for video I/O and processing:

```python
import cv2

# Check version and capabilities
print(f"OpenCV version: {cv2.__version__}")
print(f"Video backends: {cv2.getBuildInformation()[:500]}")
```

### MoviePy

For video editing and composition:

```python
from moviepy.editor import VideoFileClip

clip = VideoFileClip("input.mp4")
print(f"Duration: {clip.duration}s")
print(f"FPS: {clip.fps}")
print(f"Size: {clip.size}")
```

### ImageIO

For image sequence handling:

```python
import imageio

# List supported formats
print(imageio.formats)

# Check video support
print(imageio.plugins.ffmpeg.get_exe())
```

## AI Model Setup

### Stable Diffusion (for frame generation)

```python
from diffusers import StableDiffusionPipeline
import torch

# Load model (optimized for Jetson)
pipeline = StableDiffusionPipeline.from_pretrained(
    "stabilityai/stable-diffusion-1-5",
    torch_dtype=torch.float16,
    variant="fp16",
)

# Enable optimizations
pipeline.enable_attention_slicing()
pipeline.enable_vae_slicing()
pipeline = pipeline.to("cuda")

print("SD pipeline loaded!")
```

### Real-ESRGAN (for upscaling)

```bash
# Install Real-ESRGAN
git clone https://github.com/xinntao/Real-ESRGAN.git
cd Real-ESRGAN
pip install -e .
```

## Verification

### 1. Test Video Reading

```python
#!/usr/bin/env python3
"""Verify video processing setup"""

import cv2
import numpy as np
import os

def test_video_read():
    """Test video reading capability"""
    
    # Create test video
    test_file = "/tmp/test_video.mp4"
    
    # Generate test video
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(test_file, fourcc, 30.0, (640, 480))
    
    for i in range(30):  # 1 second at 30fps
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        out.write(frame)
    
    out.release()
    
    # Read it back
    cap = cv2.VideoCapture(test_file)
    
    if cap.isOpened():
        ret, frame = cap.read()
        cap.release()
        
        if ret:
            print("✅ Video read/write: OK")
            os.remove(test_file)
            return True
    
    print("❌ Video read/write: FAILED")
    return False

def test_libraries():
    """Test required libraries"""
    
    tests = [
        ("cv2 (OpenCV)", "import cv2"),
        ("numpy", "import numpy"),
        ("PIL", "from PIL import Image"),
        ("moviepy", "import moviepy"),
        ("torch", "import torch"),
        ("diffusers", "import diffusers"),
    ]
    
    all_ok = True
    
    for name, import_stmt in tests:
        try:
            exec(import_stmt)
            print(f"✅ {name}: OK")
        except ImportError as e:
            print(f"❌ {name}: {e}")
            all_ok = False
    
    return all_ok

if __name__ == "__main__":
    print("=== Video Processing Setup Verification ===\n")
    
    print("Testing libraries...")
    libs_ok = test_libraries()
    
    print("\nTesting video I/O...")
    video_ok = test_video_read()
    
    print("\n" + "="*40)
    if libs_ok and video_ok:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed. Please install missing dependencies.")
```

## Performance Tuning

### 1. CUDA Configuration

```bash
# Set CUDA architecture
export CUDA_ARCH_BIN="8.7"

# Memory allocation
export PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:512"

# Enable TensorRT
python -c "import tensorrt; print(f'TensorRT: {tensorrt.__version__}')"
```

### 2. Jetson-Specific Optimizations

```bash
# Enable maximum performance
sudo nvpmodel -m 0
sudo jetson_clocks

# Disable desktop (optional, for more resources)
sudo systemctl stop gdm3  # or lightdm
```

### 3. Python Optimization

```python
import torch

# Enable optimizations
torch.backends.cudnn.benchmark = True
torch.backends.cuda.matmul.allow_tf32 = True

# Memory management
torch.cuda.empty_cache()

# Check GPU
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
```

## Next Steps

- [Video Basics](./03-video-basics.md) - Learn video handling
- [Frame Generation](./04-frame-generation.md) - Generate video frames
- [Video Interpolation](./06-video-interpolation.md) - Create smooth video
