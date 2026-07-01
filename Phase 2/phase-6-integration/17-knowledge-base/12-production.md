# Production Deployment

## Systemd Service

```bash
sudo tee /etc/systemd/system/rag-api.service << 'EOF'
[Unit]
Description=RAG API Service
After=network.target ollama.service

[Service]
Type=simple
User=sergiok
WorkingDirectory=/home/sergiok
ExecStart=/usr/bin/python3 /home/sergiok/rag_api.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable rag-api
sudo systemctl start rag-api
```

## Docker Deployment

```dockerfile
FROM python:3.10-slim

RUN apt update && apt install -y curl
RUN curl -fsSL https://ollama.ai/install.sh | sh

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir \
    langchain langchain-community \
    langchain-ollama faiss-cpu

EXPOSE 5000
CMD ["python", "rag_api.py"]
```

## Monitoring

```python
import logging

logging.basicConfig(level=logging.INFO)

@app.middleware("http")
async def log_requests(request, call_next):
    logging.info(f"{request.method} {request.url}")
    return await call_next(request)
```

## Caching

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_query(question):
    return rag.query(question)
```

## Security

```python
# Add API key verification
API_KEY = os.environ.get("API_KEY")

@app.route("/query", methods=["POST"])
def query():
    if request.headers.get("X-API-Key") != API_KEY:
        return {"error": "Unauthorized"}, 401
    # ...
```

## Next Steps

- [Troubleshooting](./13-troubleshooting.md)
