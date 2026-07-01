# Writing Dockerfiles for Jetson

This guide covers creating optimized Dockerfiles for Jetson AGX Orin with JetPack 6.2.2.

## Base Images

### Official NVIDIA L4T Base

```dockerfile
FROM nvcr.io/nvidia/l4t-base:r36.2.0
```

### PyTorch Base

```dockerfile
FROM nvcr.io/nvidia/l4t-pytorch:r36.2.0-pytorch2.1.0-py3
```

### TensorFlow Base

```dockerfile
FROM nvcr.io/nvidia/l4t-tensorflow:r36.2.0-tf2.17-py3
```

## Dockerfile Best Practices

### Use multi-stage builds

```dockerfile
# Build stage
FROM python:3.12-slim as builder
RUN pip install --user some-package

# Runtime stage
FROM python:3.12-slim
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
```

### Layer ordering for caching

```dockerfile
# Install dependencies first (changes less frequently)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy code last (changes most frequently)
COPY . .
```

### Combine RUN commands

```dockerfile
RUN apt-get update && apt-get install -y \
    package1 \
    package2 \
    && rm -rf /var/lib/apt/lists/*
```

## CUDA-Enabled Dockerfile

```dockerfile
FROM nvcr.io/nvidia/l4t-base:r36.2.0

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . /app
WORKDIR /app

CMD ["python3", "app.py"]
```

## GPU Access in Container

```dockerfile
FROM nvcr.io/nvidia/l4t-pytorch:r36.2.0-pytorch2.1.0-py3

WORKDIR /workspace

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["python3", "main.py"]
```

Run with:

```bash
docker run --gpus all -it myimage
```

## Optimized for Jetson

### Small image size

```dockerfile
FROM python:3.12-slim-bookworm

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

CMD ["python3", "app.py"]
```

### Build arguments

```dockerfile
ARG CUDA_VERSION=12.2
ARG PYTHON_VERSION=3.10

FROM nvidia/cuda:${CUDA_VERSION}-devel-ubuntu22.04

RUN apt-get update && apt-get install -y python${PYTHON_VERSION}
```

## Working with Models

```dockerfile
FROM nvcr.io/nvidia/l4t-pytorch:r36.2.0-pytorch2.1.0-py3

WORKDIR /workspace

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY model_weights ./models
ENV MODEL_PATH=/workspace/models

COPY . .

CMD ["python3", "inference.py"]
```

## Expose Ports

```dockerfile
EXPOSE 8080 8443
```

Or at runtime:

```bash
docker run -p 8080:8080 -p 8443:8443 myimage
```

## Health Checks

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .

RUN pip install flask

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"

CMD ["python", "app.py"]
```

## Docker Compose Integration

```yaml
services:
  ai-service:
    build: .
    runtime: nvidia
    environment:
      - NVIDIA_VISIBLE_DEVICES=all
    volumes:
      - ./models:/models
    ports:
      - "8080:8080"
```

## Common Issues

### Python in Docker

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
```

### Permission issues

```dockerfile
RUN useradd -m -s /bin/bash appuser
USER appuser
```

### Clean up in same layer

```dockerfile
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        python3-dev \
        && apt-get clean \
        && rm -rf /var/lib/apt/lists/*
```

## Example: Ollama Dockerfile

```dockerfile
FROM nvcr.io/nvidia/l4t-base:r36.2.0

ENV DEBIAN_FRONTEND=noninteractive
ENV OLLAMA_HOST=0.0.0.0

RUN apt-get update && apt-get install -y \
    curl \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://ollama.com/install.sh | sh

WORKDIR /root
ENV OLLAMA_MODELS=/models

VOLUME ["/models"]

EXPOSE 11434

CMD ["ollama", "serve"]
```
