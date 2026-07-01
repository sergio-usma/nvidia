# Docker Basics

Docker keeps your host system clean and lets you run pre-optimized AI containers.

## Verify Docker Installation

```bash
docker --version
docker info | grep -i runtime
```

Expected: Docker should show "nvidia" as a runtime.

## Test GPU Access in Container

```bash
sudo docker run --rm --runtime nvidia nvcr.io/nvidia/l4t-base:r36.5.0 nvidia-smi
```

You should see your Orin's GPU information.

## Basic Docker Commands

### List Images

```bash
docker images
```

### List Containers

```bash
docker ps           # Running containers
docker ps -a        # All containers
```

### Run Interactive Container

```bash
docker run -it --rm nvcr.io/nvidia/l4t-pytorch:r36.5.0 python3
```

### Run with GPU

```bash
docker run --runtime nvidia -it --rm nvcr.io/nvidia/l4t-pytorch:r36.5.0 python3 -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

### Run in Background

```bash
docker run -d --runtime nvidia -p 11434:11434 --name ollama nvcr.io/nvidia/l4t-pytorch:r36.5.0
```

### Execute Command in Running Container

```bash
docker exec -it container_name bash
```

### Stop/Start Container

```bash
docker stop container_name
docker start container_name
```

### Remove Container

```bash
docker rm container_name
```

## Understanding Docker Concepts

- **Image**: Template with OS and dependencies (e.g., `nvcr.io/nvidia/l4t-pytorch:r36.5.0`)
- **Container**: Running instance of an image
- **Volume**: Persistent storage outside container
- **Port Mapping**: `-p host:container` exposes container port to host

## Persist Data with Volumes

### Bind Mount (Host Folder)

```bash
docker run --runtime nvidia -v /home/$USER/models:/models -it nvcr.io/nvidia/l4t-pytorch:r36.5.0
```

### Named Volume

```bash
docker volume create my_data
docker run -v my_data:/data -it nvcr.io/nvidia/l4t-pytorch:r36.5.0
```

## Clean Up

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Full cleanup
docker system prune -a
```

## Docker Best Practices

1. Always use `--runtime nvidia` for GPU access
2. Use images with matching L4T version (r36.5.0 for JetPack 6.2)
3. Use volumes for persistent data (models, datasets)
4. Clean up regularly to save disk space
5. Use `--rm` for temporary containers

## Next Steps

- [Docker Compose](02-docker-compose.md) - Manage multi-container applications
- [jetson-containers](03-jetson-containers.md) - Pre-built AI containers
