# Debugging Tools

This guide covers debugging tools for Python and JavaScript development on Jetson AGX Orin.

## Python Debugging

### PDB

```python
import pdb

def buggy_function(x):
    result = x * 2
    pdb.set_trace()  # Breakpoint
    return result
```

Commands: `n` (next), `s` (step), `c` (continue), `p variable` (print), `l` (list)

### IPDB

```bash
pip install ipdb
```

```python
import ipdb

def buggy_function(x):
    result = x * 2
    ipdb.set_trace()  # Interactive breakpoint
    return result
```

### Breakpoint

Python 3.7+:

```python
def buggy_function(x):
    breakpoint()  # Uses IDEBTPYTHONBREAKPOINT or pdb
    return x * 2
```

## VS Code Debugging

```json
// .vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Current File",
            "type": "python",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal"
        },
        {
            "name": "Python: Remote Attach",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "192.168.1.100",
                "port": 5678
            }
        }
    ]
}
```

## Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def function():
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    logger.critical("Critical message")
```

## Sentry for Error Tracking

```bash
pip install sentry-sdk
```

```python
import sentry_sdk

sentry_sdk.init(
    dsn="https://xxx@sentry.io/xxx",
    traces_sample_rate=1.0
)

try:
    risky_function()
except Exception as e:
    sentry_sdk.capture_exception(e)
```

## JavaScript Debugging

### Node Inspector

```bash
# Debug mode
node --inspect-brk app.js

# Chrome DevTools
# Navigate to chrome://inspect
```

### VS Code

```json
// .vscode/launch.json
{
    "type": "node",
    "request": "launch",
    "name": "Launch Program",
    "program": "${workspaceFolder}/app.js"
}
```

## Telemetry

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

def my_function():
    with tracer.start_as_current_span("my_function") as span:
        span.set_attribute("key", "value")
        result = do_work()
        span.set_attribute("result", result)
        return result
```

## Memory Debugging

```python
import tracemalloc

tracemalloc.start()

# Run code
result = expensive_function()

# Check memory
current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024 / 1024:.1f}MB")
print(f"Peak: {peak / 1024 / 1024:.1f}MB")

tracemalloc.stop()
```

## Profiling

```bash
# Profile Python
python -m cProfile -o output.prof app.py

# View profile
python -m pstats output.prof

# Or use snakeviz
pip install snakeviz
snakeviz output.prof
```

## Py-spy

```bash
pip install py-spy

# Profile running process
py-spy top -- python app.py

# Record profile
py-spy record -o profile.svg -- python app.py

# Flame graph
py-spy record -o profile.html -- python app.py
```

## Network Debugging

```python
import requests

# Verbose logging
import http.client as http_client
http_client.HTTPConnection.debuglevel = 1

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
requests_log = logging.getLogger("requests.packages.urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True
```

## curl Debugging

```bash
# Verbose
curl -v http://localhost:8000/api

# Show headers
curl -I http://localhost:8000/api

# With data
curl -X POST http://localhost:8000/api \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'

# Include auth
curl -H "Authorization: Bearer token" http://localhost:8000/api
```

## Docker Debugging

```bash
# Container logs
docker logs -f container_name

# Execute in container
docker exec -it container_name /bin/bash

# Inspect
docker inspect container_name

# Stats
docker stats container_name
```

## GPU Debugging

```bash
# Check GPU usage
nvidia-smi

# CUDA debugging
cuda-gdb ./myprogram

# Memory check
tegrastats --interval 1000
```
