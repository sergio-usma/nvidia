# API Server with FastAPI

## Table of Contents

1. [FastAPI Setup](#fastapi-setup)
2. [Ollama Integration](#ollama-integration)
3. [RAG API](#rag-api)
4. [Authentication](#authentication)

## FastAPI Setup

```bash
pip install fastapi uvicorn python-multipart
```

## Basic API Server

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

app = FastAPI(title="Jetson AI API")

class QueryRequest(BaseModel):
    prompt: str
    model: str = "qwen2.5-coder:latest"
    temperature: float = 0.7
    max_tokens: int = 2048

@app.post("/api/generate")
async def generate(request: QueryRequest):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": request.model,
                "prompt": request.prompt,
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
                "stream": False
            },
            timeout=120
        )
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/models")
async def list_models():
    response = requests.get("http://localhost:11434/api/tags")
    return response.json()

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
```

## Ollama Integration

```python
from fastapi import FastAPI
import requests

app = FastAPI()

class ChatRequest(BaseModel):
    messages: list
    model: str = "llama3.2:3b"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    response = requests.post(
        "http://localhost:11434/v1/chat/completions",
        json={
            "model": request.model,
            "messages": request.messages
        }
    )
    return response.json()

@app.post("/api/embeddings")
async def embeddings(request: dict):
    response = requests.post(
        "http://localhost:11434/v1/embeddings",
        json={
            "model": "nomic-embed-text:latest",
            "prompt": request["prompt"]
        }
    )
    return response.json()
```

## RAG API

```python
from fastapi import FastAPI, Query
from langchain_ollama import OllamaEmbeddings
from langchain.vectorstores import FAISS

app = FastAPI()

# Initialize embeddings
embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")
vectorstore = FAISS.load_local("knowledge_base", embeddings)

@app.post("/api/rag")
async def rag_query(request: dict):
    query = request["query"]
    docs = vectorstore.similarity_search(query, k=3)
    context = "\n\n".join([doc.page_content for doc in docs])
    
    # Generate response
    response = requests.post(
        "http://localhost:11434/v1/chat/completions",
        json={
            "model": "qwen2.5-coder:latest",
            "messages": [
                {"role": "system", "content": "Answer based on context."},
                {"role": "user", "content": f"Context: {context}\n\nQuestion: {query}"}
            ]
        }
    )
    
    return {
        "answer": response.json()["choices"][0]["message"]["content"],
        "sources": [doc.metadata for doc in docs]
    }
```

## Authentication

```python
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import APIKeyHeader

API_KEY = "your-secret-key"
api_key_header = APIKeyHeader(name="X-API-Key")

def verify_key(key: str = Depends(api_key_header)):
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    return key

@app.post("/api/generate", dependencies=[Depends(verify_key)])
async def generate(request: QueryRequest):
    # Your generation logic
    pass
```

## Run Server

```bash
# Development
python3 api_server.py

# Production with gunicorn
pip install gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker api_server:app
```

## Next Steps

- [SaaS Deployment](./04-saas-deployment.md) - Deploy publicly
- [Reverse Proxy](./05-reverse-proxy.md) - Nginx setup
