# Application Performance Monitoring

This guide covers APM (Application Performance Monitoring) for Jetson AGX Orin.

## Py-Spy

```bash
pip install py-spy

# Profile running process
py-spy top -- python app.py

# Generate flame graph
py-spy record -o profile.svg -- python app.py

# Profile for 30 seconds
py-spy record -o profile.svg -d 30 -- python app.py
```

## Scalene

```bash
pip install scalene

# Profile script
scalene app.py

# Profile with more detail
scalene --cpu --memory --gpu app.py
```

## cProfile

```python
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# Your code here
result = expensive_function()

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

## Memory Profiling

```python
# tracemalloc
import tracemalloc

tracemalloc.start()

# Your code
result = process_data()

current, peak = tracemalloc.get_traced_memory()
print(f"Current: {current / 1024 / 1024:.1f}MB")
print(f"Peak: {peak / 1024 / 1024:.1f}MB")

tracemalloc.stop()
```

## Line Profiler

```bash
pip install line-profiler

# Add @profile decorator
@profile
def slow_function():
    # code
    pass
```

Run:

```bash
kernprof -l -v app.py
```

## Flask Profiler

```bash
pip install flask-profiler

app.config['PROFILER'] = True

from flask_profiler import Profiler
profiler = Profiler(app)
profiler.init_app(app)
```

## OpenTelemetry

```bash
pip install opentelemetry-api opentelemetry-sdk
```

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("process_request")
def process_request():
    with tracer.start_as_current_span("database_query"):
        # Database operation
        pass
    
    with tracer.start_as_current_span("api_call"):
        # API call
        pass
```

## Datadog APM

```bash
pip install ddtrace

# Run with profiling
ddtrace-run python app.py
```

## New Relic

```bash
pip install newrelic

# Create newrelic.ini
newrelic-admin generate-config LICENSE_KEY newrelic.ini

# Run
NEW_RELIC_CONFIG_FILE=newrelic.ini newrelic-admin run-program python app.py
```

## Sentry Performance

```python
import sentry_sdk
from sentry_sdk.tracing import Transaction

sentry_sdk.init(
    dsn="https://xxx@sentry.io/xxx",
    traces_sample_rate=0.1
)

with Transaction(op="task", description="my_task") as span:
    span.set_tag("custom_tag", "value")
    # Your code
```

## Flask-APScheduler

```python
from flask import Flask
from flask_apscheduler import APScheduler

app = Flask(__name__)
scheduler = APScheduler()

@scheduler.task('interval', id='health_check', seconds=60)
def health_check():
    # Check services
    pass

scheduler.init_app(app)
scheduler.start()
```

## Metrics Collection

```python
from prometheus_client import Counter, Histogram, Gauge

request_count = Counter('app_requests_total', 'Total requests')
request_duration = Histogram('app_request_duration_seconds', 'Request duration')
active_users = Gauge('app_active_users', 'Active users')

@app.route('/')
def index():
    request_count.inc()
    with request_duration.time():
        # Process request
        pass
    return 'OK'
```

## Slow Query Logging

```python
import logging
import time

logging.basicConfig(level=logging.WARNING)

def log_slow_queries(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start
        
        if duration > 1.0:
            logging.warning(f"Slow query in {func.__name__}: {duration:.2f}s")
        
        return result
    return wrapper
```

## Django Debug Toolbar

```python
# settings.py
INSTALLED_APPS = [
    'debug_toolbar',
]

MIDDLEWARE = [
    'debug_toolbar.middleware.DebugToolbarMiddleware',
]

INTERNAL_IPS = ['127.0.0.1']
```

## Connection Pool Monitoring

```python
from sqlalchemy import create_engine

engine = create_engine('postgresql://...', pool_size=10, max_overflow=20)

# Monitor pool
def monitor_pool():
    print(f"Pool size: {engine.pool.size()}")
    print(f"Checked out: {engine.pool.checkedout()}")
    print(f"Overflow: {engine.pool.overflow()}")
```

## Async Profiling

```python
import asyncio
import aiohttp

async def measure_request(url):
    start = time.time()
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            await response.read()
    duration = time.time() - start
    print(f"Request took {duration:.2f}s")
```
