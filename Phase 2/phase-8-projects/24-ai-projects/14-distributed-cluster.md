# Project 14: Distributed AI Inference Cluster

A comprehensive guide to building a distributed inference cluster using multiple Jetson devices with load balancing, model serving, and centralized management.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [What You'll Build](#what-youll-build)
5. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Create Project Directory](#step-1-create-project-directory)
   - [Step 2: Configure Cluster](#step-2-configure-cluster)
   - [Step 3: Create Load Balancer](#step-3-create-load-balancer)
   - [Step 4: Create Node Service](#step-4-create-node-service)
   - [Step 5: Set Up Monitoring](#step-5-set-up-monitoring)
6. [Running the Cluster](#running-the-cluster)
7. [Scaling](#scaling)
8. [Troubleshooting](#troubleshooting)

---

## Overview

This project creates a distributed AI inference cluster:

- **Multiple Nodes**: Scale inference across devices
- **Load Balancing**: Distribute requests efficiently
- **Health Monitoring**: Automatic failover
- **Model Registry**: Centralized model management
- **Unified API**: Single endpoint for clients

### Why Distributed?

| Feature | Benefit |
|---------|---------|
| Throughput | Handle more requests |
| Reliability | Failover support |
| Cost | Use multiple devices |
| Scalability | Add nodes easily |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Distributed Cluster Architecture                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐ │
│   │                         LOAD BALANCER                                │ │
│   │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │ │
│   │  │ Round    │  │  Least   │  │  Health  │  │  Rate   │        │ │
│   │  │ Robin    │  │ Conns    │  │ Check    │  │ Limit   │        │ │
│   │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │ │
│   └───────┼──────────────┼──────────────┼──────────────┼───────────────┘ │
│           │              │              │              │                   │
│           └──────────────┴──────────────┼──────────────┘                   │
│                                         │                                  │
│           ┌─────────────────────────────┼─────────────────────────────┐    │
│           │                             │                             │    │
│           ▼                             ▼                             ▼    │
│   ┌──────────────┐            ┌──────────────┐            ┌──────────────┐│
│   │   Node 1    │            │   Node 2    │            │   Node N    ││
│   │ Jetson AGX  │            │ Jetson Nano  │            │   (Added)   ││
│   │ 192.168.1.100           │ 192.168.1.101│            │ 192.168.1.x ││
│   └──────┬───────┘            └──────┬───────┘            └──────┬───────┘│
│          │                           │                           │          │
│          ▼                           ▼                           ▼          │
│   ┌──────────────┐            ┌──────────────┐            ┌──────────────┐│
│   │ Ollama/LLM  │            │ Ollama/LLM  │            │ Ollama/LLM  ││
│   │ Models      │            │ Models      │            │ Models      ││
│   └──────────────┘            └──────────────┘            └──────────────┘│
│                                                                             │
│   ┌─────────────────────────────────────────────────────────────────────┐  │
│   │                        MONITORING                                  │  │
│   │  Prometheus + Grafana                                              │  │
│   └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Hardware

| Component | Requirement |
|-----------|------------|
| Jetson Devices | 2+ AGX Orin or mix |
| Network | Gigabit switch |
| Storage | Shared or local |

### Software

| Component | Installation |
|-----------|-------------|
| Docker | Part 2 |
| Ollama | Part 5 |

---

## What You'll Build

### Features

| Feature | Description |
|---------|-------------|
| Load Balancer | Distribute requests |
| Node Services | Model serving |
| Health Checks | Monitor nodes |
| Failover | Automatic recovery |
| Metrics | Prometheus/Grafana |

---

## Step-by-Step Implementation

### Step 1: Create Project Directory

```bash
mkdir -p ~/ai-projects/inference-cluster
cd ~/ai-projects/inference-cluster
mkdir -p config models services monitoring
```

### Step 2: Configure Cluster

Create `config/cluster.yaml`:

```yaml
cluster:
  name: jetson-cluster
  version: "1.0"

# Load balancer configuration
load_balancer:
  host: 0.0.0.0
  port: 8000
  algorithm: least_connections
  health_check_interval: 10
  max_retries: 3

# Node configuration
nodes:
  - name: jetson-main
    host: 192.168.1.100
    port: 8001
    role: primary
    gpu: "Orin 64GB"
    max_requests: 10
    weight: 100

  - name: jetson-secondary
    host: 192.168.1.101
    port: 8001
    role: worker
    gpu: "Orin 32GB"
    max_requests: 8
    weight: 80

  - name: jetson-nano
    host: 192.168.1.102
    port: 8001
    role: worker
    gpu: "Orin Nano 8GB"
    max_requests: 4
    weight: 40

# Model configuration
models:
  - name: llama3.2
    nodes: [jetson-main, jetson-secondary]
    replicas: 2
  
  - name: codeqwen
    nodes: [jetson-main]
    replicas: 1
  
  - name: mistral
    nodes: [jetson-secondary, jetson-nano]
    replicas: 2
```

### Step 3: Create Load Balancer

Create `services/load_balancer.py`:

```python
#!/usr/bin/env python3
"""
Load Balancer Service

Distributes inference requests across cluster nodes with health checking
and automatic failover.
"""

import os
import sys
import time
import yaml
import json
import random
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass
from threading import Thread
from flask import Flask, request, jsonify


@dataclass
class Node:
    """A cluster node."""
    name: str
    host: str
    port: int
    role: str
    gpu: str
    max_requests: int
    weight: int
    healthy: bool = True
    active_requests: int = 0
    last_health_check: float = 0
    total_requests: int = 0
    failed_requests: int = 0


class LoadBalancer:
    """
    Distributes requests across healthy nodes.
    """
    
    def __init__(self, config_path: str = 'config/cluster.yaml'):
        self.config_path = config_path
        self.nodes: Dict[str, Node] = {}
        self.health_check_thread = None
        self.running = False
        
        # Load configuration
        self._load_config()
    
    def _load_config(self):
        """Load cluster configuration."""
        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Create nodes
        for node_config in config.get('nodes', []):
            node = Node(
                name=node_config['name'],
                host=node_config['host'],
                port=node_config['port'],
                role=node_config.get('role', 'worker'),
                gpu=node_config.get('gpu', 'Unknown'),
                max_requests=node_config.get('max_requests', 10),
                weight=node_config.get('weight', 100)
            )
            self.nodes[node.name] = node
    
    def start_health_checks(self):
        """Start background health checking."""
        self.running = True
        self.health_check_thread = Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()
    
    def _health_check_loop(self):
        """Periodic health check loop."""
        while self.running:
            for node in self.nodes.values():
                self._check_node_health(node)
            time.sleep(10)  # Check every 10 seconds
    
    def _check_node_health(self, node: Node):
        """Check if a node is healthy."""
        try:
            response = requests.get(
                f"http://{node.host}:{node.port}/health",
                timeout=5
            )
            
            if response.status_code == 200:
                node.healthy = True
                node.last_health_check = time.time()
            else:
                node.healthy = False
                node.failed_requests += 1
        
        except:
            node.healthy = False
            node.failed_requests += 1
    
    def get_healthy_nodes(self) -> List[Node]:
        """Get list of healthy nodes."""
        return [
            n for n in self.nodes.values()
            if n.healthy and n.active_requests < n.max_requests
        ]
    
    def select_node(self, algorithm: str = 'least_connections') -> Optional[Node]:
        """
        Select a node using the specified algorithm.
        
        Args:
            algorithm: Selection algorithm
        
        Returns:
            Selected node or None
        """
        healthy = self.get_healthy_nodes()
        
        if not healthy:
            return None
        
        if algorithm == 'round_robin':
            return random.choice(healthy)
        
        elif algorithm == 'least_connections':
            return min(healthy, key=lambda n: n.active_requests)
        
        elif algorithm == 'weighted':
            # Weight by capacity
            weights = [n.weight for n in healthy]
            return random.choices(healthy, weights=weights)[0]
        
        return healthy[0]
    
    def forward_request(self, endpoint: str, data: Dict) -> Dict:
        """
        Forward request to selected node.
        
        Args:
            endpoint: API endpoint
            data: Request data
        
        Returns:
            Response from node
        """
        node = self.select_node()
        
        if not node:
            return {'error': 'No healthy nodes available'}
        
        # Track request
        node.active_requests += 1
        node.total_requests += 1
        
        try:
            response = requests.post(
                f"http://{node.host}:{node.port}{endpoint}",
                json=data,
                timeout=120
            )
            
            return response.json()
        
        except Exception as e:
            node.failed_requests += 1
            return {'error': str(e)}
        
        finally:
            node.active_requests -= 1
    
    def get_stats(self) -> Dict:
        """Get cluster statistics."""
        return {
            'total_nodes': len(self.nodes),
            'healthy_nodes': len(self.get_healthy_nodes()),
            'nodes': [
                {
                    'name': n.name,
                    'host': n.host,
                    'healthy': n.healthy,
                    'active_requests': n.active_requests,
                    'total_requests': n.total_requests,
                    'failed_requests': n.failed_requests,
                    'gpu': n.gpu
                }
                for n in self.nodes.values()
            ]
        }


# ============================================================================
# FLASK API
# ============================================================================

app = Flask(__name__)
balancer = None


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({'status': 'healthy'})


@app.route('/api/v1/chat', methods=['POST'])
def chat():
    """Chat completion endpoint."""
    data = request.json
    return balancer.forward_request('/api/chat', data)


@app.route('/api/v1/chat/completions', methods=['POST'])
def chat_completions():
    """OpenAI-compatible chat completions."""
    data = request.json
    return balancer.forward_request('/api/chat/completions', data)


@app.route('/api/v1/models', methods=['GET'])
def list_models():
    """List available models."""
    return balancer.forward_request('/api/models', {})


@app.route('/cluster/stats', methods=['GET'])
def stats():
    """Get cluster statistics."""
    return jsonify(balancer.get_stats())


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Main entry point."""
    global balancer
    
    # Initialize load balancer
    config_path = os.environ.get('CONFIG_PATH', 'config/cluster.yaml')
    balancer = LoadBalancer(config_path)
    
    # Start health checks
    balancer.start_health_checks()
    
    # Get configuration
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    lb_config = config.get('load_balancer', {})
    
    # Run Flask app
    host = lb_config.get('host', '0.0.0.0')
    port = lb_config.get('port', 8000)
    
    print(f"Starting load balancer on {host}:{port}")
    app.run(host=host, port=port, threaded=True)


if __name__ == '__main__':
    main()
```

### Step 4: Create Node Service

Create `services/node_service.py`:

```python
#!/usr/bin/env python3
"""
Inference Node Service

Runs on each cluster node to serve inference requests.
"""

import os
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS


app = Flask(__name__)
CORS(app)

# Configuration
NODE_NAME = os.environ.get('NODE_NAME', 'jetson-node')
NODE_HOST = os.environ.get('NODE_HOST', 'localhost')
NODE_PORT = int(os.environ.get('NODE_PORT', '8001'))
OLLAMA_BASE = os.environ.get('OLLAMA_BASE', 'http://localhost:11434')


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    # Check Ollama
    ollama_healthy = False
    try:
        response = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        ollama_healthy = response.status_code == 200
    except:
        pass
    
    return jsonify({
        'node': NODE_NAME,
        'status': 'healthy' if ollama_healthy else 'degraded',
        'ollama': ollama_healthy
    })


@app.route('/api/models', methods=['GET'])
def list_models():
    """List available models."""
    try:
        response = requests.get(f"{OLLAMA_BASE}/api/tags")
        return jsonify(response.json())
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat completion."""
    data = request.json
    
    try:
        response = requests.post(
            f"{OLLAMA_BASE}/api/chat",
            json=data,
            timeout=120
        )
        return jsonify(response.json())
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/completions', methods=['POST'])
def chat_completions():
    """OpenAI-compatible chat completions."""
    data = request.json
    
    # Extract messages
    messages = data.get('messages', [])
    model = data.get('model', 'llama3.2')
    
    # Convert to Ollama format
    ollama_data = {
        'model': model,
        'messages': messages,
        'stream': data.get('stream', False)
    }
    
    try:
        response = requests.post(
            f"{OLLAMA_BASE}/api/chat",
            json=ollama_data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Convert to OpenAI format
            return jsonify({
                'id': f'chatcmpl-{hash(result)}',
                'object': 'chat.completion',
                'created': result.get('created_at', 0),
                'model': model,
                'choices': [{
                    'index': 0,
                    'message': result.get('message', {}),
                    'finish_reason': 'stop'
                }],
                'usage': {
                    'prompt_tokens': result.get('prompt_eval_count', 0),
                    'completion_tokens': result.get('eval_count', 0),
                    'total_tokens': result.get('prompt_eval_count', 0) + result.get('eval_count', 0)
                }
            })
        
        return jsonify({'error': 'Ollama error'}), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print(f"Starting node service: {NODE_NAME}")
    app.run(host='0.0.0.0', port=NODE_PORT)
```

### Step 5: Set Up Monitoring

Create `monitoring/docker-compose.yml`:

```yaml
version: '3.8'

services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    restart: unless-stopped

  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    restart: unless-stopped
```

---

## Running the Cluster

### Start Nodes

```bash
# On each Jetson node
export NODE_NAME=jetson-main
python3 services/node_service.py
```

### Start Load Balancer

```bash
# On primary node
python3 services/load_balancer.py
```

### Access API

```bash
# Test the cluster
curl http://localhost:8000/api/models
```

---

## Scaling

### Add New Node

1. Install Ollama on new device
2. Add to `config/cluster.yaml`
3. Restart load balancer

### Increase Capacity

```yaml
nodes:
  - name: jetson-new
    host: 192.168.1.103
    port: 8001
    weight: 100  # Increase weight
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Node unhealthy | Check network, restart service |
| Requests failing | Check Ollama on node |
| Slow response | Add more nodes |

---

## License

MIT License
