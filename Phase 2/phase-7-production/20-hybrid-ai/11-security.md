# Security Best Practices

## API Security

```python
from fastapi import FastAPI, HTTPException
from fastapi.security import APIKeyHeader
import hmac

app = FastAPI()
api_keys = {"sk-abc123": {"name": "user1"}}
header = APIKeyHeader(name="X-API-Key")

@app.get("/secure")
async def secure_endpoint(key: str = Depends(header)):
    if key not in api_keys:
        raise HTTPException(403)
    return {"data": "secure"}
```

## Input Validation

```python
from pydantic import BaseModel, validator

class ChatInput(BaseModel):
    prompt: str
    max_length: int = 1000
    
    @validator('prompt')
    def validate_prompt(cls, v):
        if len(v) > 10000:
            raise ValueError('Prompt too long')
        return v
```

## Rate Limiting

```python
from fastapi import Request
from collections import defaultdict
import time

rate_limits = defaultdict(list)

async def rate_limit_middleware(request: Request, call_next):
    ip = request.client.host
    now = time.time()
    
    # Clean old requests
    rate_limits[ip] = [t for t in rate_limits[ip] if now - t < 60]
    
    if len(rate_limits[ip]) > 60:  # 60 requests per minute
        return HTTPException(429)
    
    rate_limits[ip].append(now)
    return await call_next(request)
```

## Next Steps

- [Scaling](./12-scaling.md) - Performance tuning
- [Troubleshooting](./13-troubleshooting.md) - Common issues
