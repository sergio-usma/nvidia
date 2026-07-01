# Docker Volumes and Storage

This guide covers Docker volumes, bind mounts, and storage management for Jetson AGX Orin.

## Volume Types

1. **Named volumes**: Managed by Docker
2. **Bind mounts**: Host directory mapping
3. **tmpfs mounts**: In-memory storage

## Create Named Volume

```bash
docker volume create ollama-models
```

## List Volumes

```bash
docker volume ls
```

## Inspect Volume

```bash
docker volume inspect ollama-models
```

## Mount Volume to Container

```bash
docker run -v ollama-models:/root/.ollama ollama/ollama
```

Or with long syntax:

```bash
docker run --mount source=ollama-models,target=/root/.ollama ollama/ollama
```

## Bind Mounts

Map host directory:

```bash
docker run -v /home/jetson/projects:/workspace myimage
```

Read-only bind mount:

```bash
docker run -v /home/jetson/projects:/workspace:ro myimage
```

## TMPFS Mounts

Memory-only storage:

```bash
docker run --tmpfs /tmp:rw,exec myimage
```

## Volume Driver Options

Local driver:

```bash
docker volume create --driver local \
  --opt type=none \
  --opt o=bind \
  --opt device=/mnt/data mydata
```

## Docker Compose Volumes

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama-data:/root/.ollama
      - ./models:/models

  postgres:
    image: postgres:15
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  ollama-data:
  postgres-data:
```

## Backup Volume

```bash
docker run --rm \
  -v ollama-models:/data \
  -v $(pwd):/backup \
  alpine tar cvf /backup/ollama-backup.tar /data
```

## Restore Volume

```bash
docker run --rm \
  -v ollama-models:/data \
  -v $(pwd):/backup \
  alpine tar xvf /backup/ollama-backup.tar -C /data
```

## Share Data Between Containers

```bash
# Create shared volume
docker volume create shared-data

# Container 1 writes
docker run -v shared-data:/data busybox sh -c 'echo "Hello" > /data/file.txt'

# Container 2 reads
docker run -v shared-data:/data busybox cat /data/file.txt
```

## NFS Volume

```bash
docker volume create \
  --driver local \
  --opt type=nfs \
  --opt o=addr=192.168.1.100,rw \
  --opt device=:/nfs/share \
  nfs-volume
```

## Storage Driver

Check current driver:

```bash
docker info | grep "Storage Driver"
```

For Jetson, use overlay2 (default on Ubuntu).

## Volume Cleanup

Remove unused volumes:

```bash
docker volume prune
```

Remove specific volume:

```bash
docker volume rm volume-name
```

## Performance Considerations

### For AI workloads

```bash
# Use host directory for model storage (faster)
docker run -v /fast-storage/ollama:/root/.ollama ollama/ollama
```

### For databases

```bash
# Use named volume for persistence
docker run -v postgres-data:/var/lib/postgresql/data postgres
```

## Device Storage Mount

Mount device directly:

```bash
docker run --device /dev/sda1:/dev/sda1 myimage
```

## Volume Permissions

Fix permissions:

```bash
docker run --rm -v myvolume:/data alpine chown -R 1000:1000 /data
```
