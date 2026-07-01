# Service Monitoring

This guide covers service monitoring for Jetson AGX Orin.

## Systemd Services

```bash
# List services
systemctl list-units --type=service

# Check service status
systemctl status nginx

# Service logs
journalctl -u nginx -n 50
journalctl -u nginx -f

# Restart on failure
sudo systemctl edit nginx

[Service]
Restart=on-failure
RestartSec=5
```

## Process Monitoring

```bash
# Process list
ps aux
ps aux | grep python

# Top processes
htop
btop

# Specific process monitoring
watch -n 1 'ps aux | grep python'
```

## Service Health Checks

```python
import requests
import subprocess
import time

def check_service(name, port):
    try:
        r = requests.get(f'http://localhost:{port}/health', timeout=2)
        return r.status_code == 200
    except:
        return False

def check_process(name):
    result = subprocess.run(['pgrep', '-f', name], capture_output=True)
    return result.returncode == 0

def monitor():
    services = [
        {'name': 'nginx', 'port': 80},
        {'name': 'ollama', 'port': 11434},
        {'name': 'postgres', 'port': 5432}
    ]
    
    for svc in services:
        if not check_service(svc['name'], svc['port']):
            print(f"Service {svc['name']} is down!")
            # Alert or restart

if __name__ == '__main__':
    while True:
        monitor()
        time.sleep(60)
```

## Health Check Endpoints

```python
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'uptime': time.time() - start_time
    })

@app.route('/ready')
def ready():
    if db.is_connected() and cache.is_ready():
        return jsonify({'status': 'ready'})
    return jsonify({'status': 'not ready'}), 503
```

## Prometheus Service Discovery

```yaml
scrape_configs:
  - job_name: 'services'
    dns_sd_configs:
      - names:
        - 'ollama.default.svc.cluster.local'
        type: 'A'
        port: 11434
```

## Monitoring Script

```python
#!/usr/bin/env python3
import psutil
import time
import smtplib
from email.mime.text import MIMEText

def send_alert(subject, message):
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = 'alerts@example.com'
    msg['To'] = 'admin@example.com'
    
    with smtplib.SMTP('localhost') as server:
        server.send_message(msg)

def check_system():
    # CPU
    cpu = psutil.cpu_percent(interval=1)
    if cpu > 90:
        send_alert('High CPU', f'CPU at {cpu}%')
    
    # Memory
    mem = psutil.virtual_memory()
    if mem.percent > 90:
        send_alert('High Memory', f'Memory at {mem.percent}%')
    
    # Disk
    disk = psutil.disk_usage('/')
    if disk.percent > 90:
        send_alert('High Disk', f'Disk at {disk.percent}%')
    
    # Services
    for svc in ['nginx', 'postgres', 'redis']:
        if not psutil.process_iter(['name']):
            send_alert('Service Down', f'{svc} is not running')

if __name__ == '__main__':
    while True:
        check_system()
        time.sleep(300)  # 5 minutes
```

## Uptime Monitoring

```bash
# Install uptime-kuma
docker run -d --name uptime-kuma -p 3001:3001 -v uptime-kuma:/app/data louislam/uptime-kuma
```

Access: http://jetson:3001

## Health Checks in Docker

```yaml
services:
  api:
    image: myapi
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Service Dependencies

```bash
# Visualize dependencies
systemctl list-dependencies nginx

# Dependency failed
systemctl list-units --failed
```
