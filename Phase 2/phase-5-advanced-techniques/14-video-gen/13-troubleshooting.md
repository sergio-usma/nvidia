# Video Processing Troubleshooting on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Common Issues](#common-issues)
3. [Memory Errors](#memory-errors)
4. [Performance Issues](#performance-issues)
5. [Video I/O Errors](#video-io-errors)

## Introduction

Common issues and solutions for video processing on Jetson AGX Orin.

## Common Issues

### CUDA Out of Memory

```
Error: CUDA out of memory
```

**Solutions:**
- Reduce batch size
- Enable CPU offload
- Process fewer frames at once

```python
# Enable memory optimizations
pipeline.enable_attention_slicing()
pipeline.enable_vae_slicing()
pipeline.enable_sequential_cpu_offload()
```

### Slow Processing

**Solutions:**
```bash
# Enable max performance
sudo nvpmodel -m 0
sudo jetson_clocks
```

### Video Codec Issues

```python
# Use different codec
fourcc = cv2.VideoWriter_fourcc(*'mp4v')  # Try 'XVID' or 'avc1'
```

## Memory Errors

### Fix: Clear Memory

```python
import torch

# Clear between operations
torch.cuda.empty_cache()
torch.cuda.synchronize()
```

### Fix: Reduce Resolution

```python
# Use smaller size
height, width = 384, 384
```

## Performance Issues

### Check GPU Usage

```bash
# Monitor
tegrastats

# Check clocks
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq
```

### Enable Performance Mode

```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

## Video I/O Errors

### Cannot Open Video

```python
# Check file exists
import os
print(os.path.exists("video.mp4"))

# Try different backend
cap = cv2.VideoCapture("video.mp4", cv2.CAP_FFMPEG)
```

### Wrong Colors

```python
# Convert color space
frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
```

## Additional Resources

- [OpenCV Documentation](https://docs.opencv.org/)
- [NVIDIA Jetson Forums](https://forums.developer.nvidia.com/)
- [Jetson AI Lab](https://www.jetsonai-lab.com)
