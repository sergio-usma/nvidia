# Container Monitoring and Debugging

This guide covers monitoring and debugging Docker containers on Jetson AGX Orin.

## Container Stats

Real-time resource usage:

```bash
docker stats
docker stats --no-stream container_name
```

Format output:

```bash
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
```

## Container Logs

View logs:

```bash
docker logs container_name
```

Follow in real-time:

```bash
docker logs -f container_name
```

Tail last N lines:

```bash
docker logs --tail 100 container_name
```

Timestamps:

```bash
docker logs -t container_name
```

## Container Inspect

Get detailed info:

```bash
docker inspect container_name
```

Specific fields:

```bash
docker inspect --format='{{.NetworkSettings.IPAddress}}' container_name
docker inspect --format='{{.State.Status}}' container_name
```

## Process List in Container

```bash
docker top container_name
```

## Executing Commands in Container

Interactive shell:

```bash
docker exec -it container_name /bin/bash
docker exec -it container_name /bin/sh
```

One-off command:

```bash
docker exec container_name python3 script.py
```

## Resource Usage Analysis

### CPU

```bash
docker stats --format "table {{.Name}}\t{{.CPUPerc}}"
```

### Memory

```bash
docker stats --format "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
```

### Network

```bash
docker stats --format "table {{.Name}}\t{{.NetIO}}"
```

### Block I/O

```bash
docker stats --format "table {{.Name}}\t{{.BlockIO}}"
```

## Health Checks

Check container health:

```bash
docker inspect --format='{{.State.Health.Status}}' container_name
```

View health logs:

```bash
docker inspect --format='{{range .State.Health.Log}}{{.Output}} {{end}}' container_name
```

## Network Debugging

Inspect network:

```bash
docker network inspect bridge
docker network inspect container_network_name
```

DNS lookup in container:

```bash
docker exec container_name nslookup service_name
```

Test connectivity:

```bash
docker exec container_name curl http://service:port
```

## Volume Debugging

Inspect volume:

```bash
docker volume inspect volume_name
```

Mount inside container:

```bash
docker run --rm -v volume_name:/volume busybox ls -la /volume
```

## Events

Real-time events:

```bash
docker events
docker events --filter 'container=container_name'
```

## Pruning

Clean up unused resources:

```bash
# Stopped containers
docker container prune

# Unused networks
docker network prune

# Dangling images
docker image prune

# Build cache
docker builder prune

# All
docker system prune
```

## Performance Monitoring Tools

### cAdvisor

```bash
docker run \
  --volume=/:/rootfs:ro \
  --volume=/var/run:/var/run:ro \
  --volume=/sys:/sys:ro \
  --volume=/var/lib/docker/:/var/lib/docker:ro \
  --publish=8080:8080 \
  gcr.io/cadvisor/cadvisor
```

Access at http://jetson:8080

### Glances

```bash
docker run --rm -it \
  --net=host \
  --pid=host \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  nicolargo/glances
```

## Debugging Common Issues

### Container keeps restarting

```bash
docker logs container_name
docker inspect container_name
```

### Port conflicts

```bash
docker port container_name
netstat -tulpn | grep <port>
```

### Permission denied

```bash
docker exec container_name id
docker exec container_name ls -la /app
```

### Out of memory

```bash
docker stats
docker inspect --format='{{.State.OOMKilled}}' container_name
```

## Container Attach

Attach to running container:

```bash
docker attach container_name
```

Detach: `Ctrl+P, Ctrl+Q`

## Copy Files

Copy from container:

```bash
docker cp container_name:/app/logs ./logs
```

Copy to container:

```bash
docker cp ./config container_name:/app/config
```

## Container Diff

See changes to filesystem:

```bash
docker diff container_name
```

Shows: A (added), D (deleted), C (changed)

## System Resources

Docker system df:

```bash
docker system df
docker system df -v
```

Shows disk usage by images, containers, volumes.
