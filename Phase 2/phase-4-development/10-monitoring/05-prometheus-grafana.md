# Prometheus and Grafana

This guide covers Prometheus and Grafana for monitoring Jetson AGX Orin.

## Install Prometheus

```bash
# Download
wget https://github.com/prometheus/prometheus/releases/download/v2.45.0/prometheus-2.45.0.linux-arm64.tar.gz
tar xvf prometheus-*.tar.gz
cd prometheus-*
```

## Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']

  - job_name: 'ollama'
    static_configs:
      - targets: ['localhost:11434']
```

## Node Exporter

```bash
# Install
wget https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-arm64.tar.gz

# Run
./node_exporter

# Docker
docker run -d \
  --name node_exporter \
  -p 9100:9100 \
  prom/node-exporter
```

## Custom Metrics

```python
from prometheus_client import start_http_server, Counter, Gauge
import random

requests_total = Counter('app_requests_total', 'Total requests')
processing_time = Gauge('app_processing_seconds', 'Processing time')

app.run(port=8000)

@app.route('/metrics')
def metrics():
    return generate_latest()
```

## Grafana Install

```bash
# Docker
docker run -d \
  --name grafana \
  -p 3000:3000 \
  -e GF_SECURITY_ADMIN_PASSWORD=admin \
  grafana/grafana

# Access: http://jetson:3000 (admin/admin)
```

## Dashboards

### Node Exporter Dashboard

Import ID: 1860

```json
{
  "panels": [
    {
      "type": "graph",
      "title": "CPU Usage",
      "targets": [
        {
          "expr": "100 - (avg by (instance) (rate(node_cpu_seconds_total{mode='idle'}[5m])) * 100)"
        }
      ]
    },
    {
      "type": "graph",
      "title": "Memory Usage",
      "targets": [
        {
          "expr": "node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes"
        }
      ]
    }
  ]
}
```

## Docker Monitoring

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'docker'
    static_configs:
      - targets: ['localhost:9323']
```

## Service Discovery

```yaml
scrape_configs:
  - job_name: 'services'
    dns_sd_configs:
      - names:
        - 'ollama.default.svc.cluster.local'
        - 'whisper.default.svc.cluster.local'
```

## Alerting

```yaml
# alerting_rules.yml
groups:
  - name: alerts
    rules:
      - alert: HighCPU
        expr: 100 - (avg by (instance) (rate(node_cpu_seconds_total{mode='idle'}[5m])) * 100) > 90
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High CPU usage"

      - alert: HighMemory
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100 > 85
        for: 5m
        labels:
          severity: critical
```

## Alertmanager

```yaml
# alertmanager.yml
route:
  receiver: 'email'
receivers:
  - name: 'email'
    email_configs:
      - to: 'admin@example.com'
        send_resolved: true
```

## Exporters

### GPU Exporter

```bash
docker run -d \
  --name gpu-exporter \
  -p 9445:9445 \
  --gpus all \
  nvidia/gpu-exporter
```

### Ollama Exporter

```python
from prometheus_client import start_http_server, Gauge

ollama_requests = Gauge('ollama_requests_total', 'Total Ollama requests')

@app.route('/metrics')
def metrics():
    return generate_latest()
```

## PromQL Queries

```promql
# CPU usage
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# Memory usage
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes * 100

# Network traffic
rate(node_network_receive_bytes_total[5m])

# Disk usage
node_filesystem_avail_bytes / node_filesystem_size_bytes * 100
```

## Integration with FastAPI

```python
from fastapi import FastAPI
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

app = FastAPI()

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

## Ansible Collection

```bash
# Install
ansible-galaxy collection install prometheus.prometheus
```
