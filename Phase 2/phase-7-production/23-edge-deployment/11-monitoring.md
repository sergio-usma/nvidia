# Monitoring

Implement comprehensive monitoring for your AI services to ensure reliability and performance.

## Monitoring Stack

| Component | Purpose | Port |
|-----------|---------|------|
| Prometheus | Metrics collection | 9090 |
| Grafana | Visualization | 3000 |
| Node Exporter | System metrics | 9100 |
| cAdvisor | Container metrics | 8080 |
| AlertManager | Alert routing | 9093 |

## Prometheus Setup

```bash
# Install Prometheus
sudo apt install prometheus prometheus-node-exporter

# Configure Prometheus
sudo nano /etc/prometheus/prometheus.yml
```

Prometheus config:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'node'
    static_configs:
      - targets: ['localhost:9100']

  - job_name: 'ollama'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'

  - job_name: 'api'
    static_configs:
      - targets: ['localhost:5000']
    metrics_path: '/metrics'
```

Start services:

```bash
sudo systemctl enable prometheus
sudo systemctl start prometheus
```

## Metrics Export

### Custom Metrics

```python
# api/metrics.py
from prometheus_client import Counter, Histogram, Gauge
import time

# Request metrics
request_count = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status']
)

request_duration = Histogram(
    'api_request_duration_seconds',
    'API request duration',
    ['method', 'endpoint']
)

# Model metrics
model_inferences = Counter(
    'model_inferences_total',
    'Total model inferences',
    ['model', 'status']
)

model_loaded = Gauge(
    'model_loaded',
    'Model loaded in memory',
    ['model']
)

# GPU metrics
gpu_memory_used = Gauge(
    'gpu_memory_bytes',
    'GPU memory used',
    ['device']
)

gpu_utilization = Gauge(
    'gpu_utilization_percent',
    'GPU utilization percentage',
    ['device']
)
```

### Metrics Middleware

```python
# api/middleware.py
from flask import request, g
import time
from api.metrics import request_count, request_duration

def track_metrics():
    g.start_time = time.time()
    
    def after_request(response):
        duration = time.time() - g.start_time
        
        request_count.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown',
            status=response.status_code
        ).inc()
        
        request_duration.labels(
            method=request.method,
            endpoint=request.endpoint or 'unknown'
        ).observe(duration)
        
        return response
    
    return after_request
```

## GPU Monitoring

### NVIDIA Prometheus Exporter

```bash
# Install DCGM
sudo apt install datacenter-gpu-manager

# Enable DCGM exporter
sudo systemctl enable nvidia-dcgm-exporter
sudo systemctl start nvidia-dcgm-exporter
```

### Custom GPU Metrics

```python
# scripts/gpu_metrics.py
import pynvml
import time
from prometheus_client import start_http_server, Gauge

pynvml.nvmlInit()
handle = pynvml.nvmlDeviceGetHandleByIndex(0)

gpu_temp = Gauge('gpu_temperature_celsius', 'GPU temperature')
gpu_util = Gauge('gpu_utilization_percent', 'GPU utilization')
gpu_mem_used = Gauge('gpu_memory_used_bytes', 'GPU memory used')
gpu_mem_total = Gauge('gpu_memory_total_bytes', 'GPU memory total')

def collect_metrics():
    temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
    util = pynvml.nvmlDeviceGetUtilizationRates(handle)
    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
    
    gpu_temp.set(temp)
    gpu_util.set(util.gpu)
    gpu_mem_used.set(mem_info.used)
    gpu_mem_total.set(mem_info.total)

if __name__ == '__main__':
    start_http_server(9101)
    while True:
        collect_metrics()
        time.sleep(1)
```

## Grafana Dashboards

### Dashboard JSON

```json
{
  "dashboard": {
    "title": "AI Stack Dashboard",
    "panels": [
      {
        "title": "GPU Utilization",
        "type": "graph",
        "targets": [
          {
            "expr": "gpu_utilization_percent{device=\"0\"}",
            "legendFormat": "GPU Utilization"
          }
        ],
        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8}
      },
      {
        "title": "GPU Memory",
        "type": "graph",
        "targets": [
          {
            "expr": "gpu_memory_used_bytes{device=\"0\"} / 1024^3",
            "legendFormat": "Used (GB)"
          },
          {
            "expr": "gpu_memory_total_bytes{device=\"0\"} / 1024^3",
            "legendFormat": "Total (GB)"
          }
        ],
        "gridPos": {"x": 12, "y": 0, "w": 12, "h": 8}
      },
      {
        "title": "API Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(api_request_duration_seconds_sum[5m]) / rate(api_request_duration_seconds_count[5m])",
            "legendFormat": "Avg Response Time"
          }
        ],
        "gridPos": {"x": 0, "y": 8, "w": 12, "h": 8}
      },
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(api_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ],
        "gridPos": {"x": 12, "y": 8, "w": 12, "h": 8}
      }
    ]
  }
}
```

## Alerting

### Alert Rules

```yaml
# alerts/ai-alerts.yml
groups:
  - name: ai-stack
    rules:
      - alert: HighGPUUsage
        expr: gpu_utilization_percent > 95
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "GPU usage is high"
          
      - alert: GPUOutOfMemory
        expr: (gpu_memory_used_bytes / gpu_memory_total_bytes) > 0.95
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "GPU memory is almost full"
          
      - alert: HighResponseTime
        expr: rate(api_request_duration_seconds_sum[5m]) / rate(api_request_duration_seconds_count[5m]) > 5
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "API response time is high"
          
      - alert: ServiceDown
        expr: up{job="ollama"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Ollama service is down"
```

### AlertManager Config

```yaml
# alertmanager/config.yml
route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'email'

receivers:
  - name: 'email'
    email_configs:
      - to: 'admin@example.com'
        from: 'alerts@example.com'
        smarthost: 'smtp.example.com:587'
        auth_username: 'alerts@example.com'
        auth_password: 'your-password'
```

## System Monitoring

### Resource Alerts

```bash
# Add to crontab
*/5 * * * * /home/jetson/scripts/check_resources.sh
```

```bash
#!/bin/bash
# check_resources.sh

# Check disk space
DISK_USAGE=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "WARNING: Disk usage is at ${DISK_USAGE}%"
fi

# Check memory
MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100}')
if [ "$MEM_USAGE" -gt 90 ]; then
    echo "WARNING: Memory usage is at ${MEM_USAGE}%"
fi

# Check temperature
TEMP=$(cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null | cut -c1-2)
if [ "$TEMP" -gt 80 ]; then
    echo "WARNING: CPU temperature is ${TEMP}C"
fi
```

## Log Monitoring

### Centralized Logging

```bash
# Install Loki
sudo apt install loki promtail

# Configure Promtail
sudo nano /etc/promtail/promtail.yml
```

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /var/lib/promtail/positions.yaml

clients:
  - url: http://localhost:3100/loki/api/v1/push

scrape_configs:
  - job_name: system
    static_configs:
      - targets:
        - localhost
        labels:
          job: system-logs
          __path__: /var/log/*.log
```

## Next Steps

- [Troubleshooting](./12-troubleshooting.md) - Debug and resolve issues
