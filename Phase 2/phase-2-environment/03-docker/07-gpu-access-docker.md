# GPU Access in Docker

This guide covers enabling NVIDIA GPU access in Docker containers on Jetson AGX Orin with JetPack 6.2.2.

## Prerequisites

Verify NVIDIA runtime:

```bash
docker info | grep -i nvidia
```

Expected output: `NVIDIA Runtime: default`

## Install NVIDIA Container Toolkit

If not installed:

```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt update
sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker
```

## Test GPU Access

```bash
docker run --rm --gpus all nvcr.io/nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

## Run Container with GPU

### Using --gpus flag

```bash
docker run --gpus all myimage
```

### Specific GPU

```bash
docker run --gpus '"device=0"' myimage
```

### Multiple GPUs

```bash
docker run --gpus '"device=0,1"' myimage
```

## Docker Compose with GPU

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    volumes:
      - ollama-data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]

  python-gpu:
    build: .
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=0
```

## PyTorch with GPU

```bash
docker run --gpus all -it \
    nvcr.io/nvidia/l4t-pytorch:r36.2.0-pytorch2.1.0-py3 \
    python3 -c "import torch; print(torch.cuda.is_available())"
```

Output should be `True`.

## TensorFlow with GPU

```bash
docker run --gpus all -it \
    nvcr.io/nvidia/l4t-tensorflow:r36.2.0-tf2.17-py3 \
    python3 -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

## Environment Variables

### Control GPU visibility

```bash
docker run --gpus all -e NVIDIA_VISIBLE_DEVICES=0 myimage
```

Available values:
- `all`: All GPUs
- `0,1`: Specific GPUs
- `none`: No GPU

### Disable GPU

```bash
docker run -e NVIDIA_VISIBLE_DEVICES=none myimage
```

## Device Capabilities

Check available capabilities:

```bash
docker run --rm -it nvcr.io/nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi --query-gpu=compute_cap --format=csv
```

On Jetson Orin: compute capability 8.7 (sm_87)

## Troubleshooting

### GPU not available in container

```bash
# Check NVIDIA driver
nvidia-smi

# Check Docker NVIDIA runtime
docker info | grep -i nvidia

# Reinstall container toolkit
sudo apt install --reinstall nvidia-container-toolkit
```

### CUDA version mismatch

```bash
# Check CUDA version
nvcc --version

# Use matching base image
docker run --gpus all nvcr.io/nvidia/cuda:12.2.0-devel-ubuntu22.04
```

### TensorRT in container

```bash
docker run --gpus all nvcr.io/nvidia/l4t-tensorrt:r36.2.0-tf2.17-py3
```

## GPU Monitoring in Container

```bash
docker run --gpus all --rm nvcr.io/nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi -l 1
```

Or use `tegrastats`:

```bash
docker run --privileged --rm \
    -v /usr/bin/tegrastats:/usr/bin/tegrastats \
    myimage tegrastats
```

## Performance Optimization

### Use host networking for GPU communication

```bash
docker run --gpus all --network host myimage
```

### Pin memory

```bash
docker run --gpus all \
    --runtime nvidia \
    -e NVIDIA_VISIBLE_DEVICES=all \
    myimage
```

### Use IPC for shared memory

```bash
docker run --gpus all --ipc=host myimage
```

## Multi-Container GPU Sharing

```yaml
services:
  inference:
    image: my inference-image
    runtime: nvidia
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  training:
    image: my training-image
    runtime: nvidia
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

## Verify GPU Memory

```bash
docker run --gpus all --rm \
    nvcr.io/nvidia/cuda:12.2.0-base-ubuntu22.04 \
    nvidia-smi --query-gpu=memory.free,memory.total --format=csv
```
