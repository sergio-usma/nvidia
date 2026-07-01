# Project 8: Production AI API Server

A comprehensive guide to building a secure, production-ready API server for AI services with authentication, rate limiting, monitoring, and OpenAI-compatible endpoints.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Prerequisites](#prerequisites)
5. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Install Dependencies](#step-1-install-dependencies)
   - [Step 2: Create Project Structure](#step-2-create-project-structure)
   - [Step 3: Configuration](#step-3-configuration)
   - [Step 4: Core Application](#step-4-core-application)
   - [Step 5: API Routes](#step-5-api-routes)
   - [Step 6: Security Middleware](#step-6-security-middleware)
   - [Step 7: Run the Server](#step-7-run-the-server)
6. [API Documentation](#api-documentation)
7. [Testing](#testing)
8. [Deployment](#deployment)
9. [Monitoring](#monitoring)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This project creates a production-grade API server:

- **OpenAI-Compatible Endpoints**: Use OpenAI client libraries
- **Authentication**: API key and JWT support
- **Rate Limiting**: Prevent abuse
- **Monitoring**: Health checks and metrics
- **Documentation**: Swagger/OpenAPI docs
- **Docker Support**: Easy deployment

### Why a Production API Server?

| Feature | Benefit |
|---------|---------|
| API Keys | Control access |
| Rate Limiting | Prevent abuse |
| OpenAI Compatible | Drop-in replacement |
| Monitoring | Observability |
| Docker | Easy deployment |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Production AI API Architecture                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│   │   Clients    │───▶│   FastAPI    │───▶│   Ollama     │               │
│   │ (Web/Apps)   │    │   Server     │    │   Backend    │               │
│   └──────────────┘    └──────┬───────┘    └──────────────┘               │
│                              │                                            │
│         ┌────────────────────┼────────────────────┐                     │
│         │                    │                    │                     │
│         ▼                    ▼                    ▼                     │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐              │
│  │  Auth        │     │  Rate Limit  │     │  Logging     │              │
│  │  Middleware  │     │  Middleware  │     │  Middleware  │              │
│  └──────────────┘     └──────────────┘     └──────────────┘              │
│                                                                             │
│   Endpoints:                                                                │
│   POST /v1/chat/completions    → Chat completion (OpenAI compatible)       │
│   POST /v1/embeddings          → Generate embeddings                       │
│   GET  /v1/models             → List available models                      │
│   GET  /health                → Health check                              │
│   GET  /docs                  → Swagger documentation                     │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Features

| Feature | Description |
|---------|-------------|
| OpenAI Compatibility | Use OpenAI Python SDK |
| API Key Auth | Secure access control |
| JWT Support | Token-based auth |
| Rate Limiting | Requests per minute |
| Request Logging | Full audit trail |
| Health Checks | System status |
| Swagger Docs | Interactive API explorer |
| Docker Ready | Containerized deployment |

---

## Prerequisites

### Required Software

| Component | Installation Guide |
|-----------|-------------------|
| Ollama | [Part 5: Ollama Setup](../part-5-llms/01-ollama-setup.md) |
| Python | [Part 3: Python Setup](../part-3-python-environment/01-python-setup.md) |
| Docker | [Part 2: Docker Basics](../part-2-docker/01-docker-basics.md) |

### Pre-Installation Verification

```bash
# Verify Python
python3 --version

# Verify pip
pip3 --version

# Verify Ollama
ollama --version
```

---

## Step-by-Step Implementation

### Step 1: Install Dependencies

```bash
# Create virtual environment
python3 -m venv --system-site-packages venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install API server dependencies
pip install fastapi uvicorn python-multipart \
    python-jose[cryptography] passlib[bcrypt] \
    python-dotenv slowapi httpx \
    langchain langchain-community \
    pydantic pydantic-settings
```

### Step 2: Create Project Structure

```bash
# Create project directory
mkdir -p ~/ai-projects/api-server
cd ~/ai-projects/api-server

# Create subdirectories
mkdir -p app app/routes app/middleware app/models

# Create .env file
touch .env
```

### Step 3: Configuration

Create `.env`:

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Security
API_KEYS=your-secret-api-key-here,another-key
JWT_SECRET=change-this-to-a-random-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600

# Rate Limiting
RATE_LIMIT_REQUESTS=60
RATE_LIMIT_WINDOW=60

# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=llama3.2
EMBEDDING_MODEL=nomic-embed-text
```

### Step 4: Core Application

Create `app/main.py`:

```python
#!/usr/bin/env python3
"""
Production AI API Server

A FastAPI-based server providing OpenAI-compatible endpoints
for local AI models via Ollama.

Author: Your Name
Version: 1.0.0
"""

# ============================================================================
# IMPORTS
# ============================================================================
import os
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from dotenv import load_dotenv
import httpx

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# API Settings
API_HOST = os.getenv('API_HOST', '0.0.0.0')
API_PORT = int(os.getenv('API_PORT', '8000'))
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

# Ollama Settings
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
DEFAULT_MODEL = os.getenv('DEFAULT_MODEL', 'llama3.2')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL', 'nomic-embed-text')

# Security Settings
API_KEYS = os.getenv('API_KEYS', '').split(',')
JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')

# ============================================================================
# LIFESPAN EVENTS
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting AI API Server...")
    logger.info(f"Ollama URL: {OLLAMA_BASE_URL}")
    logger.info(f"Default Model: {DEFAULT_MODEL}")
    
    # Verify Ollama connection
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
            if response.status_code == 200:
                logger.info("Ollama connection verified")
            else:
                logger.warning(f"Ollama returned status {response.status_code}")
    except Exception as e:
        logger.warning(f"Cannot connect to Ollama: {e}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down AI API Server...")


# ============================================================================
# CREATE APP
# ============================================================================

app = FastAPI(
    title="AI API Server",
    description="Production API for local AI models",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests."""
    start_time = datetime.now()
    
    response = await call_next(request)
    
    duration = (datetime.now() - start_time).total_seconds()
    logger.info(
        f"{request.method} {request.url.path} "
        f"{response.status_code} {duration:.3f}s"
    )
    
    return response


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error"}
    )


# ============================================================================
# HEALTH CHECKS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check Ollama
    ollama_status = "unknown"
    models = []
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
            if response.status_code == 200:
                data = response.json()
                models = [m['name'] for m in data.get('models', [])]
                ollama_status = "connected"
            else:
                ollama_status = "error"
    except Exception as e:
        ollama_status = f"disconnected: {e}"
    
    return {
        "status": "healthy" if ollama_status == "connected" else "degraded",
        "ollama": ollama_status,
        "models": models,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check for Kubernetes."""
    return {"status": "ready"}


# ============================================================================
# ROOT
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "AI API Server",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# ============================================================================
# INCLUDE ROUTES
# ============================================================================

# Import and include route modules
from app.routes import chat, embeddings, models

app.include_router(chat.router, prefix="/v1", tags=["Chat"])
app.include_router(embeddings.router, prefix="/v1", tags=["Embeddings"])
app.include_router(models.router, prefix="/v1", tags=["Models"])
```

### Step 5: API Routes

Create `app/routes/chat.py`:

```python
"""
Chat Completions API

OpenAI-compatible chat completion endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import httpx
import os

router = APIRouter()

# Security
API_KEYS = os.getenv('API_KEYS', '').split(',')
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify API key."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key"
        )
    
    # Support Bearer token or simple API key
    if api_key.startswith('Bearer '):
        api_key = api_key[7:]
    
    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    return api_key


# Request models
class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = Field(default=os.getenv('DEFAULT_MODEL', 'llama3.2'))
    messages: List[Message]
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=0.9, ge=0, le=1)
    max_tokens: Optional[int] = Field(default=2048, ge=1)
    stream: bool = False
    stop: Optional[List[str]] = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


# Routes
@router.post("/chat/completions")
async def create_chat_completion(
    request: ChatCompletionRequest,
    api_key: str = Depends(verify_api_key)
):
    """Create a chat completion."""
    
    ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    
    # Convert messages to Ollama format
    ollama_messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            if request.stream:
                # Streaming response
                response = await client.post(
                    f"{ollama_url}/api/chat",
                    json={
                        "model": request.model,
                        "messages": ollama_messages,
                        "stream": True,
                        "options": {
                            "temperature": request.temperature,
                            "top_p": request.top_p,
                            "num_predict": request.max_tokens,
                            "stop": request.stop
                        }
                    },
                    stream=True
                )
                
                async def generate():
                    async for line in response.aiter_lines():
                        if line:
                            data = line
                            if data.startswith('data: '):
                                data = data[6:]
                            yield f"data: {data}\n\n"
                
                return generate()
            
            else:
                # Non-streaming response
                response = await client.post(
                    f"{ollama_url}/api/chat",
                    json={
                        "model": request.model,
                        "messages": ollama_messages,
                        "stream": False,
                        "options": {
                            "temperature": request.temperature,
                            "top_p": request.top_p,
                            "num_predict": request.max_tokens,
                            "stop": request.stop
                        }
                    }
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=response.text
                    )
                
                result = response.json()
                
                # Convert to OpenAI format
                return {
                    "id": f"chatcmpl-{hash(result.get('message', {}).get('content', ''))}",
                    "object": "chat.completion",
                    "created": result.get('created_at', 0),
                    "model": request.model,
                    "choices": [{
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": result.get('message', {}).get('content', '')
                        },
                        "finish_reason": "stop"
                    }],
                    "usage": {
                        "prompt_tokens": result.get('prompt_eval_count', 0),
                        "completion_tokens": result.get('eval_count', 0),
                        "total_tokens": result.get('prompt_eval_count', 0) + result.get('eval_count', 0)
                    }
                }
    
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Request to Ollama timed out"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
```

Create `app/routes/embeddings.py`:

```python
"""
Embeddings API

OpenAI-compatible embeddings endpoint.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import List
import httpx
import os

router = APIRouter()

# Security
API_KEYS = os.getenv('API_KEYS', '').split(',')
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify API key."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key"
        )
    if api_key.startswith('Bearer '):
        api_key = api_key[7:]
    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return api_key


# Request models
class EmbeddingsRequest(BaseModel):
    model: str = Field(default=os.getenv('EMBEDDING_MODEL', 'nomic-embed-text'))
    input: List[str]


# Routes
@router.post("/embeddings")
async def create_embeddings(
    request: EmbeddingsRequest,
    api_key: str = Depends(verify_api_key)
):
    """Create embeddings for text."""
    
    ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    
    embeddings = []
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            for text in request.input:
                response = await client.post(
                    f"{ollama_url}/api/embeddings",
                    json={
                        "model": request.model,
                        "prompt": text
                    }
                )
                
                if response.status_code != 200:
                    continue
                
                result = response.json()
                embeddings.append({
                    "object": "embedding",
                    "embedding": result.get('embedding', []),
                    "index": len(embeddings)
                })
        
        return {
            "object": "list",
            "data": embeddings,
            "model": request.model,
            "usage": {
                "prompt_tokens": sum(len(e['embedding']) for e in embeddings),
                "total_tokens": sum(len(e['embedding']) for e in embeddings)
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
```

Create `app/routes/models.py`:

```python
"""
Models API

List available models.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import APIKeyHeader
import httpx
import os

router = APIRouter()

# Security
API_KEYS = os.getenv('API_KEYS', '').split(',')
api_key_header = APIKeyHeader(name="Authorization", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify API key."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key"
        )
    if api_key.startswith('Bearer '):
        api_key = api_key[7:]
    if api_key not in API_KEYS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return api_key


# Routes
@router.get("/models")
async def list_models(api_key: str = Depends(verify_api_key)):
    """List available models."""
    
    ollama_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{ollama_url}/api/tags")
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail="Failed to get models"
                )
            
            data = response.json()
            models = data.get('models', [])
            
            return {
                "object": "list",
                "data": [{
                    "id": m['name'],
                    "object": "model",
                    "created": m.get('created_at', 0),
                    "owned_by": "ollama"
                } for m in models]
            }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
```

### Step 6: Create __init__.py

Create `app/__init__.py`:

```python
# App package
```

Create `app/routes/__init__.py`:

```python
# Routes package
```

### Step 7: Run the Server

```bash
# Activate environment
cd ~/ai-projects/api-server
source venv/bin/activate

# Run with uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## API Documentation

### Authentication

All endpoints require an API key:

```bash
# Using header
curl -H "Authorization: Bearer your-secret-api-key-here" \
  http://localhost:8000/v1/models
```

### Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/v1/chat/completions` | POST | Chat completion |
| `/v1/embeddings` | POST | Create embeddings |
| `/v1/models` | GET | List models |
| `/docs` | GET | Swagger UI |

### OpenAI Compatibility

Use with OpenAI Python SDK:

```python
from openai import OpenAI

client = OpenAI(
    api_key="your-secret-api-key-here",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="llama3.2",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

---

## Testing

```bash
# Health check
curl http://localhost:8000/health

# List models
curl -H "Authorization: Bearer your-secret-api-key-here" \
  http://localhost:8000/v1/models

# Chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer your-secret-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

---

## Deployment

### Using Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## Monitoring

### Prometheus Metrics

Add prometheus client:

```bash
pip install prometheus-client
```

```python
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter('api_requests_total', 'Total API requests')
REQUEST_LATENCY = Histogram('api_request_duration_seconds', 'Request latency')
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| 401 Unauthorized | Check API key in header |
| Connection refused | Start Ollama |
| Slow responses | Use smaller model |
| Rate limited | Wait and retry |

---

## License

MIT License
