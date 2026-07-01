# Docker Containers

Containerize your AI services for consistent deployment and easy management.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Docker Host (Jetson AGX Orin)               │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐│
│  │   Ollama    │  │  Whisper    │  │      API Server         ││
│  │  Container  │  │  Container  │  │      Container           ││
│  │  :11434    │  │  :8001      │  │      :5000              ││
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘│
│         │                │                      │              │
│         └────────────────┼──────────────────────┘              │
│                          │                                     │
│                    ┌─────┴─────┐                               │
│                    │  Network  │                               │
│                    │   Bridge   │                               │
│                    └───────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

## Dockerfile for Ollama

Create `Dockerfile.ollama`:

```dockerfile
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV OLLAMA_HOST=0.0.0.0:11434
ENV OLLAMA_MODELS=/models

# Install dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy CUDA libraries
COPY cuda-libs /usr/local/cuda/lib64

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Create model directory
RUN mkdir -p /models

# Expose port
EXPOSE 11434

# Run Ollama
CMD ["serve"]
```

## Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  ollama:
    build:
      context: .
      dockerfile: Dockerfile.ollama
    image: jetson-ollama:latest
    container_name: ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama-models:/models
      - ./config:/config
    environment:
      - OLLAMA_HOST=0.0.0.0:11434
      - OLLAMA_GPU_LAYERS=99
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped
    networks:
      - ai-network

  whisper:
    image: abdladeh/faster-whisper-jetson:latest
    container_name: faster-whisper
    ports:
      - "8001:8001"
    volumes:
      - whisper-cache:/root/.cache/whisper
    environment:
      - MODEL=medium
      - DEVICE=cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    restart: unless-stopped
    networks:
      - ai-network

  api-server:
    build:
      context: ./api
      dockerfile: Dockerfile
    container_name: ai-api-server
    ports:
      - "5000:5000"
    volumes:
      - ./api:/app
    environment:
      - OLLAMA_HOST=ollama:11434
      - WHISPER_HOST=whisper:8001
    depends_on:
      - ollama
      - whisper
    restart: unless-stopped
    networks:
      - ai-network

  nginx:
    image: nginx:latest
    container_name: nginx-proxy
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - api-server
    restart: unless-stopped
    networks:
      - ai-network

networks:
  ai-network:
    driver: bridge

volumes:
  ollama-models:
  whisper-cache:
```

## Build and Run

```bash
# Build all services
docker compose build

# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop all services
docker compose down
```

## GPU Configuration

### Docker GPU Access

Ensure NVIDIA Container Toolkit is installed:

```bash
# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
    sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt update
sudo apt install -y nvidia-container-toolkit

# Restart Docker
sudo systemctl restart docker
```

### Verify GPU Access

```bash
# Test GPU in container
docker run --rm --gpus all nvidia/cuda:12.6.0-base-ubuntu22.04 nvidia-smi
```

## Multi-Container Management

### Service Health Checks

```yaml
services:
  ollama:
    # ... other config
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

### Scaling Services

```bash
# Scale API server
docker compose up -d --scale api-server=3

# Load balancer required for scaling
# Add nginx with upstream configuration
```

## Volume Management

### Backup Volumes

```bash
# Backup Ollama models
docker run --rm -v ollama-models:/data -v $(pwd):/backup alpine \
    tar czf /backup/ollama-backup.tar.gz -C /data .
```

### Restore Volumes

```bash
# Restore Ollama models
docker volume create ollama-models
docker run --rm -v ollama-models:/data -v $(pwd):/backup alpine \
    tar xzf /backup/ollama-backup.tar.gz -C /data
```

## Resource Limits

```yaml
services:
  ollama:
    deploy:
      resources:
        limits:
          memory: 16G
          cpus: '4'
        reservations:
          memory: 8G
          cpus: '2'
```

## Custom Docker Runtime

### Use NVIDIA Runtime

```bash
# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

Update `daemon.json`:

```json
{
    "runtimes": {
        "nvidia": {
            "path": "nvidia-container-runtime",
            "runtimeArgs": []
        }
    },
    "default-runtime": "nvidia"
}
```

## Next Steps

- [Reverse Proxy](./07-reverse-proxy.md) - Secure access via proxy
- [Authentication](./08-authentication.md) - Add authentication layer
