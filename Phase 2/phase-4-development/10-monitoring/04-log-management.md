# Log Management

This guide covers log management for Jetson AGX Orin.

## Python Logging

```python
import logging
import logging.handlers

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.handlers.RotatingFileHandler(
            'app.log', maxBytes=10*1024*1024, backupCount=5
        )
    ]
)

logger = logging.getLogger(__name__)
logger.info("Application started")
```

## Log Levels

- DEBUG: Detailed info for debugging
- INFO: Confirmation things work
- WARNING: Something unexpected
- ERROR: Serious problem
- CRITICAL: Very serious error

## Structured Logging

```python
import json
import logging

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            'timestamp': self.formatTime(record),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        return json.dumps(log_data)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

## Log Rotation

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'app.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
logger.addHandler(handler)

# Or TimedRotatingFileHandler
from logging.handlers import TimedRotatingFileHandler

handler = TimedRotatingFileHandler(
    'app.log',
    when='midnight',
    interval=1,
    backupCount=30
)
```

## Centralized Logging

### ELK Stack

```yaml
# docker-compose.yml
version: '3'
services:
  elasticsearch:
    image: elasticsearch:7.17.0
    environment:
      - discovery.type=single-node
    
  kibana:
    image: kibana:7.17.0
    ports:
      - "5601:5601"
    
  logstash:
    image: logstash:7.17.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
```

### Loki

```yaml
# docker-compose.yml
services:
  loki:
    image: grafana/loki:2.8.0
    ports:
      - "3100:3100"
    
  promtail:
    image: grafana/promtail:2.8.0
    volumes:
      - /var/log:/var/log
      - ./promtail.yml:/etc/promtail/config.yml
```

## Syslog

```python
import logging
import logging.handlers

handler = logging.handlers.SysLogHandler(address='/dev/log')
logger.addHandler(handler)

logger.error("Error message via syslog")
```

## Journald

```python
import logging
from systemd.journal import JournalHandler

logger = logging.getLogger(__name__)
logger.addHandler(JournalHandler(SYSLOG_IDENTIFIER='myapp'))

logger.info("Message to journal")
```

## Log Analysis

```bash
# Search logs
grep "ERROR" /var/log/app.log
tail -f /var/log/app.log

# Count errors
grep -c "ERROR" /var/log/app.log

# Analyze with awk
awk '/ERROR/ {count++} END {print count}' /var/log/app.log
```

## Cloud Logging

### Python GCP

```bash
pip install google-cloud-logging
```

```python
import google.cloud.logging

client = google.cloud.logging.Client()
client.setup_logging()

import logging
logger = logging.getLogger(__name__)
logger.error("Logged to GCP")
```

### AWS CloudWatch

```bash
pip install watchtower
```

```python
import watchtower
import logging

logging.basicConfig(handlers=[watchtower.CloudWatchLogHandler()])
logger = logging.getLogger(__name__)
logger.error("Logged to CloudWatch")
```

## Application Logs

```python
# FastAPI
from fastapi import FastAPI
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

@app.get("/")
def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "Hello"}
```

## Request Logging

```python
import logging

# Morgan equivalent for Python
class RequestLoggingMiddleware:
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger(__name__)
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            self.logger.info(f"{scope['method']} {scope['path']}")
        await self.app(scope, receive, send)
```

## Error Tracking

```python
# Sentry
import sentry_sdk

sentry_sdk.init(dsn="https://xxx@sentry.io/xxx")

try:
    risky_operation()
except Exception as e:
    sentry_sdk.capture_exception(e)
```

## Log Aggregation

```bash
# Use journalctl
journalctl -u myservice
journalctl -f
journalctl --since "1 hour ago"

# Filter by priority
journalctl -p err
```

## Performance Logging

```python
import time
import logging

logger = logging.getLogger(__name__)

def timer(func):
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"{func.__name__} took {elapsed:.3f}s")
        return result
    return wrapper

@timer
def process_data():
    pass
```
