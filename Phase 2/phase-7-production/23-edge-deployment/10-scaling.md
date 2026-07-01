# Scaling

Scale your AI services to handle increased load and provide high availability.

## Scaling Strategies

| Strategy | Description | Use Case |
|----------|-------------|----------|
| Vertical | Add more resources | Single service growth |
| Horizontal | Add more instances | Load distribution |
| Caching | Cache responses | Repeated requests |
| Queue | Async processing | Long-running tasks |

## Horizontal Scaling

### Load Balancer Configuration

```
                    ┌─────────────┐
               ────▶│  Nginx LB   │───────┐
                    └─────────────┘       │
                    ┌─────────────┐       │
               ────▶│  API Server │───────┤
                    └─────────────┘       │
                    ┌─────────────┐       │
               ────▶│  API Server │───────┼────▶ Clients
                    └─────────────┘       │
                    ┌─────────────┐       │
               ────▶│  API Server │───────┘
                    └─────────────┘
```

### Nginx Load Balancer

```nginx
upstream api_backend {
    least_conn;
    
    server 192.168.1.100:5000 weight=5;
    server 192.168.1.101:5000 weight=5;
    server 192.168.1.102:5000 weight=3;
    
    keepalive 32;
}

server {
    location / {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_next_upstream error timeout http_502;
    }
}
```

## Service Discovery

### Consul Setup

```bash
# Install Consul
curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | \
    sudo tee /etc/apt/sources.list.d/hashicorp.list

sudo apt update && sudo apt install consul
```

### Service Registration

```python
# api/consul.py
import consul
import requests

c = consul.Consul(host='192.168.1.100')

def register_service():
    c.agent.service.register(
        'ai-api',
        service_id='ai-api-01',
        address='192.168.1.100',
        port=5000,
        check={
            'http': 'http://192.168.1.100:5000/health',
            'interval': '10s',
            'timeout': '5s'
        }
    )

def get_service_addresses():
    _, services = c.agent.services()
    return [f"{s['Address']}:{s['Port']}" for s in services.values()]
```

## Caching Strategy

### Redis Cache

```bash
# Install Redis
sudo apt install redis-server

# Configure for AI cache
sudo nano /etc/redis/redis.conf
```

Redis config:

```
maxmemory 2gb
maxmemory-policy allkeys-lru
save ""
appendonly no
```

### Cache Implementation

```python
# api/cache.py
import redis
import json
from functools import wraps

r = redis.Redis(host='localhost', port=6379, db=0)

def cached(key_prefix, ttl=3600):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{args}:{kwargs}"
            
            # Try cache first
            cached = r.get(cache_key)
            if cached:
                return json.loads(cached)
            
            # Call function
            result = f(*args, **kwargs)
            
            # Cache result
            r.setex(cache_key, ttl, json.dumps(result))
            
            return result
        return decorated
    return decorator

@cached("ollama:model:", ttl=7200)
def get_model_info(model_name):
    # This will be cached for 2 hours
    return ollama.show(model_name)
```

### Cache Warming

```python
# scripts/warm_cache.py
import ollama
import time

MODELS = ['qwen2.5-coder', 'llama3.2', 'mistral']

def warm_cache():
    for model in MODELS:
        print(f"Warming cache for {model}...")
        
        # Pre-load model
        ollama.chat(model, messages=[{"role": "user", "content": "test"}])
        
        # Get model info
        info = ollama.show(model)
        
        print(f"  {model} ready")
        time.sleep(1)

if __name__ == "__main__":
    warm_cache()
```

## Message Queues

### Celery Configuration

```bash
# Install Celery
pip install celery redis
```

```python
# tasks/celery_app.py
from celery import Celery
from celery.config import Config

app = Celery('ai_tasks')
app.config_from_object({
    'broker_url': 'redis://localhost:6379/1',
    'result_backend': 'redis://localhost:6379/2',
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json'],
    'task_routes': {
        'tasks.ollama.*': {'queue': 'ollama'},
        'tasks.whisper.*': {'queue': 'whisper'},
    }
})

# tasks/ollama_tasks.py
from celery_app import app
import ollama

@app.task
def generate_response(model, prompt):
    response = ollama.chat(model=model, messages=[{"role": "user", "content": prompt}])
    return response

@app.task
def transcribe_audio(audio_path):
    # Whisper transcription task
    pass
```

### Start Workers

```bash
# Start Ollama worker
celery -A celery_app worker -Q ollama -c 2

# Start Whisper worker  
celery -A celery_app worker -Q whisper -c 1
```

## Auto-Scaling

### Kubernetes on Jetson

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ai-api
  template:
    metadata:
      labels:
        app: ai-api
    spec:
      containers:
      - name: api
        image: jetson-ai-api:latest
        resources:
          limits:
            nvidia.com/gpu: 1
            memory: "8Gi"
          requests:
            memory: "4Gi"
        ports:
        - containerPort: 5000
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: ai-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ai-api
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

## Performance Optimization

### Model Caching

```python
# api/model_pool.py
import ollama
from threading import Lock

class ModelPool:
    def __init__(self):
        self.models = {}
        self.lock = Lock()
    
    def preload(self, model_name):
        with self.lock:
            if model_name not in self.models:
                # Pre-load model
                ollama.chat(model_name, messages=[])
                self.models[model_name] = True
    
    def ensure_loaded(self, model_name):
        with self.lock:
            if model_name not in self.models:
                self.preload(model_name)

model_pool = ModelPool()

# Pre-load on startup
for model in ['qwen2.5-coder', 'llama3.2']:
    model_pool.preload(model)
```

### Connection Pooling

```python
# api/database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    "postgresql://user:pass@localhost/ai",
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True
)
```

## Next Steps

- [Monitoring](./11-monitoring.md) - Track performance
- [Troubleshooting](./12-troubleshooting.md) - Debug issues
