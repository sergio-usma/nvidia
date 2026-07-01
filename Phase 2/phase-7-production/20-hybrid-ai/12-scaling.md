# Performance and Scaling

## Caching

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def cached_generate(prompt_hash, model):
    # Expensive generation
    pass

def get_cache_key(prompt, model):
    return hashlib.md5(f"{prompt}:{model}".encode()).hexdigest()
```

## Load Balancing

```python
# Multiple Ollama instances
OLLAMA_URLS = [
    "http://localhost:11434",
    "http://localhost:11435",
    "http://localhost:11436"
]

def get_next_server():
    return OLLAMA_URLS[roundRobin]
```

## Queue System

```python
from queue import Queue
import threading

task_queue = Queue()

def worker():
    while True:
        task = task_queue.get()
        process_task(task)
        task_queue.task_done()

# Start workers
for _ in range(4):
    t = threading.Thread(target=worker)
    t.start()
```

## Next Steps

- [Troubleshooting](./13-troubleshooting.md) - Common issues
