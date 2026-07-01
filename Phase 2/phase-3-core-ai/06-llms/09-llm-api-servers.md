# LLM API Servers

This guide covers setting up API servers for LLM inference on Jetson AGX Orin.

## Ollama API Server

Ollama comes with a built-in API:

```bash
# Start Ollama server
ollama serve

# API available at http://localhost:11434
```

### Generate Endpoint

```bash
curl http://localhost:11434/api/generate \
  -d '{
    "model": "llama2",
    "prompt": "Explain quantum computing",
    "stream": false
  }'
```

### Chat Endpoint

```bash
curl http://localhost:11434/api/chat \
  -d '{
    "model": "llama2",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

### Embeddings

```bash
curl http://localhost:11434/api/embeddings \
  -d '{
    "model": "nomic-embed-text",
    "prompt": "The quick brown fox"
  }'
```

## Flask API with Ollama

```python
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

OLLAMA_URL = "http://localhost:11434"

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": data.get("model", "llama2"),
            "prompt": data["prompt"],
            "stream": False
        }
    )
    return jsonify(response.json())

@app.route('/chat', methods=['POST'])
def chat():
    data = request.json
    response = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={
            "model": data.get("model", "llama2"),
            "messages": data["messages"]
        }
    )
    return jsonify(response.json())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## FastAPI with Ollama

```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

class Message(BaseModel):
    role: str
    content: str

class GenerateRequest(BaseModel):
    model: str = "llama2"
    prompt: str

class ChatRequest(BaseModel):
    model: str = "llama2"
    messages: List[Message]

@app.post("/generate")
async def generate(req: GenerateRequest):
    # Implementation
    return {"result": "generated text"}

@app.post("/chat")
async def chat(req: ChatRequest):
    # Implementation
    return {"response": "chat response"}
```

## llama.cpp API Server

```bash
# Start server
llama-server -m model.gguf -c 4096 -ngl 1 --port 8080
```

### API Endpoints

```bash
# Completion
curl http://localhost:8080/completion \
  -d '{"prompt": "Hello", "n_predict": 50}'

# Embedding
curl http://localhost:8080/embedding \
  -d '{"content": "Hello world"}'
```

## Node.js API Server

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const app = express();
app.use(express.json());

const ollama = new Ollama({ host: 'http://localhost:11434' });

app.post('/generate', async (req, res) => {
  const { model, prompt } = req.body;
  const response = await ollama.generate({
    model: model || 'llama2',
    prompt
  });
  res.json(response);
});

app.post('/chat', async (req, res) => {
  const { model, messages } = req.body;
  const response = await ollama.chat({
    model: model || 'llama2',
    messages
  });
  res.json(response);
});

app.listen(3000, () => {
  console.log('API server running on port 3000');
});
```

## Streaming Responses

```python
from flask import Response, stream_with_context

@app.route('/stream', methods=['POST'])
def stream():
    data = request.json
    
    def generate():
        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": data["model"],
                "prompt": data["prompt"],
                "stream": True
            },
            stream=True
        )
        
        for line in response.iter_lines():
            if line:
                yield f"data: {line}\n\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream'
    )
```

## Authentication

```python
from functools import wraps
import secrets

API_KEYS = {"secret-key-123": "user1"}

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token or not token.replace('Bearer ', '') in API_KEYS:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

@app.route('/generate', methods=['POST'])
@require_auth
def generate():
    # Implementation
    pass
```

## Rate Limiting

```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=get_remote_address)

@app.route('/generate', methods=['POST'])
@limiter.limit("10 per minute")
def generate():
    # Implementation
    pass
```

## Production with Gunicorn

```bash
pip install gunicorn

gunicorn -w 4 -b 0.0.0.0:5000 "app:app" --worker-class gthread
```

## Docker Deployment

```yaml
# docker-compose.yml
services:
  api:
    build: .
    ports:
      - "5000:5000"
    environment:
      - OLLAMA_HOST=host.docker.internal:11434
```
