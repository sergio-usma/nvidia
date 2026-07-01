# System Monitoring

## Health Check API

```python
from fastapi import FastAPI
import psutil

app = FastAPI()

@app.get("/health")
def health():
    return {
        "status": "healthy",
        "cpu": psutil.cpu_percent(),
        "memory": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent
    }

@app.get("/metrics")
def metrics():
    return {
        "cpu_percent": psutil.cpu_percent(interval=1),
        "memory_gb": psutil.virtual_memory().used / 1e9,
        "disk_gb": psutil.disk_usage('/').used / 1e9
    }
```

## Prometheus Export

```bash
pip install prometheus-client
```

```python
from prometheus_client import start_http_server, Counter, Gauge

requests_total = Counter('requests_total', 'Total requests')
in_flight = Gauge('in_flight_requests', 'Requests in flight')

@app.middleware("http")
async def track_requests(request, call_next):
    in_flight.inc()
    requests_total.inc()
    response = await call_next(request)
    in_flight.dec()
    return response
```

## Next Steps

- [Security](./11-security.md) - Security best practices
- [Scaling](./12-scaling.md) - Performance tuning
