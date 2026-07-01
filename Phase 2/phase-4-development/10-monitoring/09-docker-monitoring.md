# Docker Monitoring

This guide covers Docker container monitoring for Jetson AGX Orin.

## Docker Stats

```bash
# Real-time stats
docker stats

# All containers
docker stats --no-stream

# Format output
docker stats --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
```

## cAdvisor

```bash
# Run cAdvisor
docker run \
  --volume=/:/rootfs:ro \
  --volume=/var/run:/var/run:ro \
  --volume=/sys:/sys:ro \
  --volume=/var/lib/docker/:/var/lib/docker:ro \
  --publish=8080:8080 \
  gcr.io/cadvisor/cadvisor:v0.47.0

# Access
# http://jetson:8080
```

## Prometheus Docker Metrics

```yaml
# docker-compose.yml
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  cadvisor:
    image: gcr.io/cadvisor/cadvisor:v0.47.0
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
    ports:
      - "8080:8080"
```

## Container Health

```bash
# Inspect health
docker inspect --format='{{.State.Health.Status}}' container_name

# Health logs
docker inspect --format='{{range .State.Health.Log}}{{.Output}} {{end}}' container_name
```

## Docker Events

```bash
# Real-time events
docker events

# Filter events
docker events --filter 'type=container'
docker events --filter 'event=start'
docker events --filter 'image=nginx'
```

## Container Logs

```bash
# View logs
docker logs container_name

# Follow
docker logs -f container_name

# Tail
docker logs --tail 100 container_name

# Timestamps
docker logs -t container_name
```

## Prometheus Metrics for Docker

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
```

## Resource Alerts

```yaml
# alerts.yml
groups:
  - name: docker
    rules:
      - alert: HighContainerCPU
        expr: sum(rate(container_cpu_usage_seconds_total[5m])) by (container_label_name) > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: High CPU usage

      - alert: ContainerDown
        expr: up{job="cadvisor"} == 0
        for: 1m
        labels:
          severity: critical
```

## Monitoring Script

```python
import docker
import time
import smtplib
from email.mime.text import MIMEText

client = docker.from_env()

def check_containers():
    for container in client.containers.list():
        stats = container.stats(stream=False)
        
        cpu = calculate_cpu_percent(stats)
        mem = calculate_mem_percent(stats)
        
        print(f"{container.name}: CPU {cpu:.1f}%, MEM {mem:.1f}%")
        
        if cpu > 90 or mem > 90:
            send_alert(f"{container.name} resource warning")

def calculate_cpu_percent(stats):
    cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
               stats['precpu_stats']['cpu_usage']['total_usage']
    system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                   stats['precpu_stats']['system_cpu_usage']
    cpu_count = stats['cpu_stats'].get('online_cpus', 1)
    
    if system_delta > 0:
        return (cpu_delta / system_delta) * cpu_count * 100.0
    return 0

def calculate_mem_percent(stats):
    mem_usage = stats['memory_stats']['usage']
    mem_limit = stats['memory_stats']['limit']
    return (mem_usage / mem_limit) * 100

if __name__ == '__main__':
    while True:
        check_containers()
        time.sleep(60)
```

## Portainer

```bash
# Install Portainer
docker volume create portainer_data
docker run -d \
  --name portainer \
  -p 9000:9000 \
  -p 8000:8000 \
  --restart always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer:latest
```

Access: http://jetson:9000

## Container Resource Limits

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## Auto-restart on Failure

```yaml
services:
  app:
    restart_policy:
      condition: on-failure
      delay: 5s
      max_attempts: 3
      window: 120s
```
