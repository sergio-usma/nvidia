# Ollama Integration

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Model Management](#model-management)
4. [API Usage](#api-usage)
5. [Tool Integration](#tool-integration)
6. [Advanced Configuration](#advanced-configuration)

## Introduction

Ollama provides an easy way to run large language models locally with OpenAI-compatible APIs. Perfect for integrating with AI coding tools on Jetson.

## Installation

### Install Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Or verify existing installation
ollama --version
```

### Start Ollama Service

```bash
# Start service
ollama serve

# Or as systemd service
sudo systemctl enable ollama
sudo systemctl start ollama
```

## Model Management

### Pull Models

```bash
# Coding models (recommended)
ollama pull qwen2.5-coder:latest
ollama pull qwen2.5-coder:14b
ollama pull codeqwen:latest
ollama pull qwen3-coder:latest
ollama pull granite3.3:latest

# General models
ollama pull llama3.2:3b
ollama pull mistral:latest
ollama pull mistral-nemo:latest

# Reasoning models
ollama pull deepseek-r1:8b

# Embedding models
ollama pull nomic-embed-text:latest
```

### List Models

```bash
ollama list
```

### Remove Models

```bash
ollama rm model-name
```

## API Usage

### Chat Completions

```python
import requests

response = requests.post(
    "http://localhost:11434/v1/chat/completions",
    json={
        "model": "qwen2.5-coder:latest",
        "messages": [
            {"role": "user", "content": "Write a Python function"}
        ],
        "temperature": 0.7
    }
)

print(response.json()["choices"][0]["message"]["content"])
```

### Text Completions

```bash
curl http://localhost:11434/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen2.5-coder:latest",
    "prompt": "Write hello world in Python",
    "stream": false
  }'
```

### Embeddings

```python
response = requests.post(
    "http://localhost:11434/v1/embeddings",
    json={
        "model": "nomic-embed-text:latest",
        "prompt": "text to embed"
    }
)

print(response.json()["embedding"])
```

## Tool Integration

### Connect to OpenCode

```yaml
# ~/.config/opencode/config.yaml
provider: ollama
model: qwen2.5-coder:latest
```

### Connect to OpenClaw

```yaml
provider: ollama
model: qwen2.5-coder:latest
api_base: http://localhost:11434/v1
```

### VS Code (Continue)

```python
# ~/.continue/config.py
from continuedev.src.continuedev.models.llms import OpenAI

llm = OpenAI(
    model="qwen2.5-coder:latest",
    api_key="not-needed",
    api_base="http://localhost:11434/v1"
)
```

### Aider

```bash
# Use with Aider
aider --model ollama/qwen2.5-coder
# or
aider --model openai/qwen2.5-coder --openai-api-base http://localhost:11434/v1
```

## Advanced Configuration

### Environment Variables

```bash
# Custom host/port
export OLLAMA_HOST=0.0.0.0:11434

# Models location
export OLLAMA_MODELS=/path/to/models

# GPU layers
export GGML_CUDA_ENABLE=1
```

### Model Configuration

```bash
# Create custom model
mkdir -p ~/.ollama/models
cat > ~/.ollama/models/Modelfile << 'EOF'
FROM qwen2.5-coder:latest

PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40

SYSTEM You are an expert coding assistant.
EOF

ollama create my-coder -f ~/.ollama/models/Modelfile
```

### Multiple Models

```bash
# Run multiple instances on different ports
OLLAMA_PORT=11434 ollama serve &
OLLAMA_PORT=11435 ollama serve &
```

## Troubleshooting

### Connection Refused

```bash
# Check if Ollama is running
ps aux | grep ollama

# Start Ollama
ollama serve

# Or start as service
sudo systemctl start ollama
```

### Model Not Found

```bash
# Pull model
ollama pull qwen2.5-coder:latest

# Verify
ollama list
```

### Out of Memory

```bash
# Use smaller model
ollama pull qwen2.5-coder:7b

# Check available memory
free -h
```

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/v1/chat/completions` | Chat completion |
| POST | `/v1/completions` | Text completion |
| POST | `/v1/embeddings` | Get embeddings |
| GET | `/v1/models` | List models |
| GET | `/api/tags` | List models (Ollama native) |

### Streaming

```python
import requests

response = requests.post(
    "http://localhost:11434/v1/chat/completions",
    json={
        "model": "qwen2.5-coder:latest",
        "messages": [{"role": "user", "content": "Hello"}],
        "stream": True
    },
    stream=True
)

for line in response.iter_lines():
    if line:
        print(line.decode())
```

## Performance Tips

### Use Quantized Models

```bash
# Smaller, faster models
ollama pull qwen2.5-coder:7b
ollama pull codeqwen:7b
```

### Limit Context

```python
response = requests.post(
    "http://localhost:11434/v1/chat/completions",
    json={
        "model": "qwen2.5-coder:latest",
        "messages": [...],
        "options": {
            "num_ctx": 2048  # Reduce context
        }
    }
)
```

### Use GPU

```bash
# Ensure GPU is used
# Ollama auto-detects GPU on Jetson
# Check with:
curl http://localhost:11434/api/tags
```

## Systemd Service

```bash
sudo tee /etc/systemd/system/ollama.service << 'EOF'
[Unit]
Description=Ollama Service
After=network.target

[Service]
Type=simple
User=sergiok
ExecStart=/usr/local/bin/ollama serve
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama
```

## Next Steps

- [VS Code Integration](./09-vscode-integration.md)
- [Model Selection](./10-model-selection.md)
- [Custom Prompts](./11-custom-prompts.md)
