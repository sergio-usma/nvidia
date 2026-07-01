# Monitoring & Observability

## Logging

```python
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("app.log")
    ]
)

logger = logging.getLogger(__name__)
```

## Metrics

```python
from prometheus_client import Counter, Histogram, start_http_server

requests_total = Counter("requests_total", "Total requests")
generation_duration = Histogram("generation_duration_seconds", "Generation time")

@app.route("/generate")
def generate():
    requests_total.inc()
    with generation_duration.time():
        result = model.generate(prompt)
    return result
```

## Health Checks

```python
@app.get("/health")
def health():
    return {
        "status": "healthy",
        "ollama": check_ollama(),
        "memory": get_memory_usage()
    }

def check_ollama():
    import requests
    try:
        requests.get("http://localhost:11434/api/tags")
        return "ok"
    except:
        return "error"
```

## Next Steps

- [Best Practices](./10-best-practices.md) - Jetson-specific practices
