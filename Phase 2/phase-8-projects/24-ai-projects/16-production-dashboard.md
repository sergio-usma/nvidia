# Project 16: Production AI Dashboard

A comprehensive guide to building a production monitoring dashboard for all AI services running on Jetson AGX Orin with real-time metrics, alerting, and system health monitoring.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [What You'll Build](#what-youll-build)
5. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Install Dependencies](#step-1-install-dependencies)
   - [Step 2: Create Project Directory](#step-2-create-project-directory)
   - [Step 3: Create System Monitor](#step-3-create-system-monitor)
   - [Step 4: Create Dashboard Server](#step-4-create-dashboard-server)
   - [Step 5: Create Web Interface](#step-5-create-web-interface)
6. [Running the Dashboard](#running-the-dashboard)
7. [Advanced Configuration](#advanced-configuration)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This project creates a comprehensive production dashboard:

- **Real-time Metrics**: GPU, CPU, RAM monitoring
- **Service Health**: Ollama, Whisper, Piper status
- **Request Analytics**: Track API usage
- **Alerts**: Threshold-based notifications
- **Historical Data**: Time-series graphs
- **Multi-node View**: Cluster monitoring

### Dashboard Features

| Feature | Description |
|---------|-------------|
| GPU Monitoring | Utilization, memory, temperature |
| Service Status | Health checks |
| Request Metrics | Analytics |
| Alerts | Threshold notifications |
| API | External integrations |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Production Dashboard Architecture                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐   │
│   │                         DASHBOARD SERVER                             │   │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐          │   │
│   │  │  Flask   │  │ WebSocket│  │Prometheus│  │  Alerts  │          │   │
│   │  │  Server  │  │   IO     │  │ Metrics  │  │  Engine  │          │   │
│   │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘          │   │
│   └───────┼──────────────┼──────────────┼──────────────┼───────────────┘   │
│           │              │              │              │                    │
│           └──────────────┴──────────────┴──────────────┘                    │
│                                                                             │
│   ┌───────────────────────────┬─────────────────────────────┐               │
│   │                      DATA SOURCES                        │               │
│   │                                                           │               │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │               │
│   │  │   jtop  │  │  psutil │  │ pynvml  │  │ Services │ │               │
│   │  │(Jetson) │  │ (System)│  │  (GPU)  │  │  (REST) │ │               │
│   │  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │               │
│   │                                                           │               │
│   └───────────────────────────────────────────────────────────┘               │
│                                                                             │
│   Outputs:                                                                  │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│   │  Web UI      │  │ Prometheus   │  │  Alerts     │                   │
│   │  Dashboard   │  │  Metrics    │  │  (Email/    │                   │
│   │              │  │             │  │   Slack)    │                   │
│   └──────────────┘  └──────────────┘  └──────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Component | Installation |
|-----------|-------------|
| Flask | Python package |
| psutil | System monitoring |
| pynvml | GPU monitoring |

### Pre-Installation

```bash
# Check Python
python3 --version

# Check pip
pip3 --version
```

---

## What You'll Build

### Features

| Feature | Description |
|---------|-------------|
| GPU Metrics | Real-time monitoring |
| Service Health | Status checks |
| Request Tracking | API analytics |
| Alerting | Threshold alerts |
| Historical Data | Time-series |

---

## Step-by-Step Implementation

### Step 1: Install Dependencies

```bash
pip3 install flask flask-socketio prometheus-client psutil pynvml requests websocket-client
```

### Step 2: Create Project Directory

```bash
mkdir -p ~/ai-projects/production-dashboard
cd ~/ai-projects/production-dashboard
mkdir -p monitor static templates data
```

### Step 3: Create System Monitor

Create `monitor/system_monitor.py`:

```python
#!/usr/bin/env python3
"""
System Monitor Module

Collects real-time system metrics including GPU, CPU, memory, and service health.
"""

import os
import time
import psutil
import requests
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SystemMetrics:
    """System metrics snapshot."""
    timestamp: float = field(default_factory=time.time)
    cpu_percent: float = 0
    cpu_count: int = 0
    memory_total: int = 0
    memory_used: int = 0
    memory_percent: float = 0
    disk_total: int = 0
    disk_used: int = 0
    disk_percent: float = 0


@dataclass
class GPUMetrics:
    """GPU metrics snapshot."""
    timestamp: float = field(default_factory=time.time)
    available: bool = False
    utilization: float = 0
    memory_total: int = 0
    memory_used: int = 0
    memory_percent: float = 0
    temperature: float = 0
    power_usage: float = 0


@dataclass
class ServiceStatus:
    """Service health status."""
    name: str
    healthy: bool = False
    response_time: float = 0
    error: Optional[str] = None
    last_check: float = field(default_factory=time.time)


class SystemMonitor:
    """
    Monitors system metrics and service health.
    """
    
    def __init__(self):
        self.running = False
        self.metrics_history: List[SystemMetrics] = []
        self.gpu_history: List[GPUMetrics] = []
        
        # Service endpoints to monitor
        self.services: Dict[str, str] = {
            'ollama': 'http://localhost:11434/api/tags',
            'whisper': 'http://localhost:8001/health',
            'piper': 'http://localhost:8002/health',
            'api': 'http://localhost:5000/health'
        }
        
        self.service_statuses: Dict[str, ServiceStatus] = {}
        
        # Initialize GPU
        self.gpu_available = False
        self._init_gpu()
    
    def _init_gpu(self):
        """Initialize GPU monitoring."""
        try:
            import pynvml
            pynvml.nvmlInit()
            self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self.gpu_available = True
            print("GPU monitoring initialized")
        except Exception as e:
            print(f"GPU monitoring not available: {e}")
            self.gpu_available = False
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        metrics = SystemMetrics()
        
        # CPU
        metrics.cpu_percent = psutil.cpu_percent(interval=0.1)
        metrics.cpu_count = psutil.cpu_count()
        
        # Memory
        mem = psutil.virtual_memory()
        metrics.memory_total = mem.total
        metrics.memory_used = mem.used
        metrics.memory_percent = mem.percent
        
        # Disk
        disk = psutil.disk_usage('/')
        metrics.disk_total = disk.total
        metrics.disk_used = disk.used
        metrics.disk_percent = disk.percent
        
        return metrics
    
    def get_gpu_metrics(self) -> GPUMetrics:
        """Get current GPU metrics."""
        metrics = GPUMetrics()
        
        if not self.gpu_available:
            return metrics
        
        try:
            import pynvml
            
            # Utilization
            util = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
            metrics.utilization = util.gpu
            
            # Memory
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
            metrics.memory_total = mem_info.total
            metrics.memory_used = mem_info.used
            metrics.memory_percent = (mem_info.used / mem_info.total) * 100
            
            # Temperature
            metrics.temperature = pynvml.nvmlDeviceGetTemperature(
                self.gpu_handle,
                pynvml.NVML_TEMPERATURE_GPU
            )
            
            # Power
            metrics.power_usage = pynvml.nvmlDeviceGetPowerUsage(self.gpu_handle) / 1000.0
            
            metrics.available = True
        
        except Exception as e:
            print(f"GPU metrics error: {e}")
            metrics.available = False
        
        return metrics
    
    def check_service_health(self, name: str, url: str) -> ServiceStatus:
        """Check health of a service."""
        status = ServiceStatus(name=name)
        
        try:
            start = time.time()
            response = requests.get(url, timeout=5)
            status.response_time = time.time() - start
            status.healthy = response.status_code == 200
            status.error = None if status.healthy else f"HTTP {response.status_code}"
        
        except Exception as e:
            status.healthy = False
            status.error = str(e)
        
        status.last_check = time.time()
        return status
    
    def check_all_services(self) -> Dict[str, ServiceStatus]:
        """Check health of all services."""
        for name, url in self.services.items():
            self.service_statuses[name] = self.check_service_health(name, url)
        
        return self.service_statuses
    
    def get_all_metrics(self) -> Dict:
        """Get all metrics."""
        system = self.get_system_metrics()
        gpu = self.get_gpu_metrics()
        services = self.check_all_services()
        
        return {
            'timestamp': time.time(),
            'system': {
                'cpu_percent': system.cpu_percent,
                'cpu_count': system.cpu_count,
                'memory': {
                    'total': system.memory_total,
                    'used': system.memory_used,
                    'percent': system.memory_percent
                },
                'disk': {
                    'total': system.disk_total,
                    'used': system.disk_used,
                    'percent': system.disk_percent
                }
            },
            'gpu': {
                'available': gpu.available,
                'utilization': gpu.utilization,
                'memory': {
                    'total': gpu.memory_total,
                    'used': gpu.memory_used,
                    'percent': gpu.memory_percent
                },
                'temperature': gpu.temperature,
                'power_usage': gpu.power_usage
            },
            'services': {
                name: {
                    'healthy': s.healthy,
                    'response_time': s.response_time,
                    'error': s.error,
                    'last_check': s.last_check
                }
                for name, s in services.items()
            }
        }
    
    def start_monitoring(self, interval: int = 1):
        """Start background monitoring."""
        self.running = True
        
        def monitor_loop():
            while self.running:
                # Collect metrics
                system = self.get_system_metrics()
                gpu = self.get_gpu_metrics()
                
                # Store in history
                self.metrics_history.append(system)
                self.gpu_history.append(gpu)
                
                # Keep only last hour of data
                if len(self.metrics_history) > 3600:
                    self.metrics_history = self.metrics_history[-3600:]
                
                if len(self.gpu_history) > 3600:
                    self.gpu_history = self.gpu_history[-3600:]
                
                time.sleep(interval)
        
        thread = threading.Thread(target=monitor_loop, daemon=True)
        thread.start()
    
    def stop_monitoring(self):
        """Stop background monitoring."""
        self.running = False
    
    def get_history(self, duration: int = 60) -> Dict:
        """Get historical metrics."""
        now = time.time()
        cutoff = now - duration
        
        system_data = [
            {
                'timestamp': m.timestamp,
                'cpu_percent': m.cpu_percent,
                'memory_percent': m.memory_percent
            }
            for m in self.metrics_history
            if m.timestamp > cutoff
        ]
        
        gpu_data = [
            {
                'timestamp': m.timestamp,
                'utilization': m.utilization,
                'memory_percent': m.memory_percent,
                'temperature': m.temperature
            }
            for m in self.gpu_history
            if m.timestamp > cutoff
        ]
        
        return {
            'system': system_data,
            'gpu': gpu_data
        }


# ============================================================================
# ALERT SYSTEM
# ============================================================================

class AlertManager:
    """
    Manages alerts based on threshold violations.
    """
    
    def __init__(self):
        self.alerts: List[Dict] = []
        self.thresholds = {
            'cpu_percent': 90,
            'memory_percent': 90,
            'gpu_utilization': 95,
            'gpu_memory_percent': 90,
            'gpu_temperature': 85
        }
    
    def check_metrics(self, metrics: Dict):
        """Check metrics against thresholds and generate alerts."""
        timestamp = time.time()
        
        # CPU alert
        if metrics['system']['cpu_percent'] > self.thresholds['cpu_percent']:
            self.add_alert(
                'high_cpu',
                f"CPU usage at {metrics['system']['cpu_percent']:.1f}%"
            )
        
        # Memory alert
        if metrics['system']['memory_percent'] > self.thresholds['memory_percent']:
            self.add_alert(
                'high_memory',
                f"Memory usage at {metrics['system']['memory_percent']:.1f}%"
            )
        
        # GPU alerts
        if metrics['gpu']['available']:
            if metrics['gpu']['utilization'] > self.thresholds['gpu_utilization']:
                self.add_alert(
                    'high_gpu_util',
                    f"GPU utilization at {metrics['gpu']['utilization']:.1f}%"
                )
            
            if metrics['gpu']['temperature'] > self.thresholds['gpu_temperature']:
                self.add_alert(
                    'high_gpu_temp',
                    f"GPU temperature at {metrics['gpu']['temperature']}°C"
                )
        
        # Service alerts
        for name, status in metrics['services'].items():
            if not status['healthy']:
                self.add_alert(
                    'service_down',
                    f"Service '{name}' is down: {status.get('error', 'Unknown error')}"
                )
    
    def add_alert(self, alert_type: str, message: str):
        """Add a new alert."""
        # Avoid duplicate alerts
        for alert in self.alerts[-10:]:
            if alert['type'] == alert_type:
                return
        
        alert = {
            'type': alert_type,
            'message': message,
            'timestamp': time.time()
        }
        
        self.alerts.append(alert)
        print(f"ALERT: {alert_type} - {message}")
    
    def get_alerts(self, duration: int = 3600) -> List[Dict]:
        """Get recent alerts."""
        now = time.time()
        cutoff = now - duration
        
        return [
            a for a in self.alerts
            if a['timestamp'] > cutoff
        ]
```

### Step 4: Create Dashboard Server

Create `dashboard/app.py`:

```python
#!/usr/bin/env python3
"""
Production Dashboard Server

Web server for monitoring AI services with real-time updates.
"""

import os
import time
import json
from flask import Flask, render_template, jsonify, Response
from flask_socketio import SocketIO
from prometheus_client import Counter, Histogram, generate_latest

from monitor.system_monitor import SystemMonitor, AlertManager


# Initialize
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
monitor = SystemMonitor()
alerts = AlertManager()

# Metrics
REQUEST_COUNT = Counter('dashboard_requests_total', 'Total requests')
REQUEST_LATENCY = Histogram('dashboard_request_duration_seconds', 'Request latency')


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('index.html')


@app.route('/api/metrics')
def api_metrics():
    """Get current metrics."""
    return jsonify(monitor.get_all_metrics())


@app.route('/api/history')
def api_history():
    """Get historical metrics."""
    duration = int(request.args.get('duration', 60))
    return jsonify(monitor.get_history(duration))


@app.route('/api/alerts')
def api_alerts():
    """Get recent alerts."""
    duration = int(request.args.get('duration', 3600))
    return jsonify(alerts.get_alerts(duration))


@app.route('/metrics')
def prometheus_metrics():
    """Prometheus metrics endpoint."""
    return Response(
        generate_latest(),
        mimetype='text/plain'
    )


@app.route('/health')
def health():
    """Health check."""
    return jsonify({'status': 'healthy'})


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

def broadcast_metrics():
    """Broadcast metrics to connected clients."""
    while True:
        metrics = monitor.get_all_metrics()
        
        # Check alerts
        alerts.check_metrics(metrics)
        
        # Broadcast
        socketio.emit('metrics', metrics)
        
        socketio.sleep(1)  # Update every second


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Start monitoring
    monitor.start_monitoring()
    
    # Start broadcast thread
    socketio.start_background_task(broadcast_metrics)
    
    # Run server
    print("Starting production dashboard...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
```

### Step 5: Create Web Interface

Create `templates/index.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>AI Production Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@latest"></script>
    <script src="https://cdn.socket.io/4.0.0/socket.io.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Arial, sans-serif;
            background: #1a1a2e;
            color: #e8e8e8;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        
        h1 { color: #e94560; margin-bottom: 20px; }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #2a2a4a;
        }
        
        .card h3 {
            color: #a0a0a0;
            font-size: 14px;
            text-transform: uppercase;
            margin-bottom: 15px;
        }
        
        .metric {
            font-size: 36px;
            font-weight: bold;
            color: #4ade80;
        }
        
        .metric.warning { color: #fbbf24; }
        .metric.danger { color: #f87171; }
        
        .progress-bar {
            background: #0f3460;
            height: 10px;
            border-radius: 5px;
            overflow: hidden;
            margin-top: 10px;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #4ade80, #22c55e);
            transition: width 0.3s;
        }
        
        .service-list { margin-top: 10px; }
        
        .service {
            display: flex;
            justify-content: space-between;
            padding: 10px;
            background: #0f3460;
            border-radius: 8px;
            margin-bottom: 8px;
        }
        
        .service.healthy { border-left: 3px solid #4ade80; }
        .service.unhealthy { border-left: 3px solid #f87171; }
        
        .alert {
            background: #7f1d1d;
            border-left: 3px solid #f87171;
            padding: 12px;
            border-radius: 8px;
            margin-bottom: 8px;
        }
        
        .alert-time {
            font-size: 12px;
            color: #a0a0a0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 AI Production Dashboard</h1>
        
        <!-- System Metrics -->
        <div class="grid">
            <div class="card">
                <h3>CPU Usage</h3>
                <div class="metric" id="cpu-metric">0%</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="cpu-bar" style="width: 0%"></div>
                </div>
            </div>
            
            <div class="card">
                <h3>Memory Usage</h3>
                <div class="metric" id="mem-metric">0%</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="mem-bar" style="width: 0%"></div>
                </div>
            </div>
            
            <div class="card">
                <h3>GPU Utilization</h3>
                <div class="metric" id="gpu-metric">0%</div>
                <div class="progress-bar">
                    <div class="progress-fill" id="gpu-bar" style="width: 0%"></div>
                </div>
            </div>
            
            <div class="card">
                <h3>GPU Temperature</h3>
                <div class="metric" id="temp-metric">0°C</div>
            </div>
        </div>
        
        <!-- Charts -->
        <div class="grid">
            <div class="card">
                <h3>CPU & Memory History</h3>
                <canvas id="systemChart"></canvas>
            </div>
            
            <div class="card">
                <h3>GPU History</h3>
                <canvas id="gpuChart"></canvas>
            </div>
        </div>
        
        <!-- Services & Alerts -->
        <div class="grid">
            <div class="card">
                <h3>Services</h3>
                <div class="service-list" id="services"></div>
            </div>
            
            <div class="card">
                <h3>Recent Alerts</h3>
                <div id="alerts"></div>
            </div>
        </div>
    </div>
    
    <script>
        // Charts
        const systemCtx = document.getElementById('systemChart').getContext('2d');
        const gpuCtx = document.getElementById('gpuChart').getContext('2d');
        
        const systemChart = new Chart(systemCtx, {
            type: 'line',
            data: { labels: [], datasets: [] },
            options: { responsive: true, scales: { y: { max: 100 } } }
        });
        
        const gpuChart = new Chart(gpuCtx, {
            type: 'line',
            data: { labels: [], datasets: [] },
            options: { responsive: true, scales: { y: { max: 100 } } }
        });
        
        // Socket.IO
        const socket = io();
        
        socket.on('metrics', (data) => {
            // Update CPU
            const cpu = data.system.cpu_percent;
            document.getElementById('cpu-metric').textContent = cpu.toFixed(1) + '%';
            document.getElementById('cpu-bar').style.width = cpu + '%';
            
            // Update Memory
            const mem = data.system.memory_percent;
            document.getElementById('mem-metric').textContent = mem.toFixed(1) + '%';
            document.getElementById('mem-bar').style.width = mem + '%';
            
            // Update GPU
            if (data.gpu.available) {
                const gpu = data.gpu.utilization;
                document.getElementById('gpu-metric').textContent = gpu.toFixed(1) + '%';
                document.getElementById('gpu-bar').style.width = gpu + '%';
                
                document.getElementById('temp-metric').textContent = 
                    data.gpu.temperature.toFixed(0) + '°C';
            }
            
            // Update Services
            const servicesDiv = document.getElementById('services');
            servicesDiv.innerHTML = '';
            
            for (const [name, status] of Object.entries(data.services)) {
                const div = document.createElement('div');
                div.className = `service ${status.healthy ? 'healthy' : 'unhealthy'}`;
                div.innerHTML = `
                    <span>${name}</span>
                    <span>${status.healthy ? '✓' : '✗'}</span>
                `;
                servicesDiv.appendChild(div);
            }
        });
    </script>
</body>
</html>
```

---

## Running the Dashboard

```bash
# Start the dashboard
python3 dashboard/app.py

# Access the dashboard
# Open http://localhost:5000
```

---

## Alert Configuration

Configure alert thresholds:

```python
alerts.thresholds = {
    'cpu_percent': 90,
    'memory_percent': 90,
    'gpu_utilization': 95,
    'gpu_temperature': 85
}
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| GPU not showing | Check pynvml |
| Services not found | Check service URLs |
| Charts not updating | Check Socket.IO |

---

## License

MIT License
