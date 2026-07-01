# llama.cpp Integration

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Running Models](#running-models)
4. [API Server](#api-server)
5. [Tool Integration](#tool-integration)
6. [Performance Optimization](#performance-optimization)

## Introduction

llama.cpp is a high-performance inference engine for GGUF models. It runs natively on ARM64 and provides excellent performance on Jetson AGX Orin.

## Installation

### Build from Source

```bash
# Install dependencies
sudo apt install -y build-essential cmake git

# Clone repository
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp

# Build with CUDA support
cmake -B build -DCMAKE_BUILD_TYPE=Release \
    -DGGML_CUDA=ON \
    -DGGML_ACCELERATE=ON

cmake --build build -j$(nproc)
```

### Pre-built Binaries

```bash
# Download latest release
wget https://github.com/ggerganov/llama.cpp/releases/latest/download/llama-cli-aarch64
wget https://github.com/ggerganov/llama.cpp/releases/latest/download/llama-server-aarch64

chmod +x llama-*-aarch64
sudo mv llama-*-aarch64 /usr/local/bin/
```

## Running Models

### Using llama-cli

**Qwen3 Coder (your model)**:
```bash
llama-cli \
    -m ~/unsloth/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-UD-Q4_K_XL.gguf \
    -ngl 999 \
    -c 4096 \
    -t 12 \
    --temp 0.7 \
    -n -1
```

**GLM-4.7 Flash**:
```bash
llama-cli \
    -m ~/unsloth/GLM-4.7-Flash-GGUF/GLM-4.7-Flash-UD-Q4_K_XL.gguf \
    -ngl 999 \
    -c 4096 \
    -t 12
```

**Qwen 3.5 27B**:
```bash
llama-cli \
    -m ~/.cache/llama.cpp/unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf \
    -ngl 999 \
    -c 4096 \
    -t 12
```

### Parameters

| Parameter | Description | Recommended |
|-----------|-------------|--------------|
| `-m` | Model path | Required |
| `-ngl` | GPU layers (999 = all) | 999 |
| `-c` | Context size | 2048-4096 |
| `-t` | Threads | 12 |
| `--temp` | Temperature | 0.7 |
| `-n` | Max tokens | -1 (unlimited) |
| `--no-mmap` | Disable memory mapping | For low RAM |

### Batch Processing

```bash
# Process multiple prompts
echo -e "Hello\nHow are you?" | llama-cli -m model.gguf -ngl 999
```

## API Server

### Start Server

```bash
# Basic server
llama-server \
    -m ~/unsloth/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-UD-Q4_K_XL.gguf \
    -ngl 999 \
    -c 4096 \
    -port 8080
```

### Server Options

```bash
llama-server \
    -m model.gguf \
    -ngl 999 \
    -c 4096 \
    -port 8080 \
    --host 0.0.0.0 \
    -t 12 \
    --parallel 4 \
    --cont-batching
```

### API Endpoints

Once running on port 8080:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/chat/completions` | POST | Chat completions |
| `/v1/completions` | POST | Text completions |
| `/v1/models` | GET | List models |
| `/embeddings` | POST | Get embeddings |

### Example API Calls

```bash
# Chat completion
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-coder",
    "messages": [{"role": "user", "content": "Write hello world in Python"}],
    "temperature": 0.7
  }'

# Text completion
curl http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen3-coder",
    "prompt": "Write hello world in Python",
    "max_tokens": 100
  }'
```

## Tool Integration

### Connect to OpenCode

```yaml
# ~/.config/opencode/config.yaml
provider: llama.cpp
model: /home/user/unsloth/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-UD-Q4_K_XL.gguf
api_base: http://localhost:8080/v1
```

### Connect to OpenClaw

```yaml
provider: llama.cpp
model: /home/user/unsloth/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-UD-Q4_K_XL.gguf
api_base: http://localhost:8080/v1
```

### Connect to VS Code (Continue)

```python
# ~/.continue/config.py
from continuedev.src.continuedev.models.llms import OpenAI

llm = OpenAI(
    model="qwen3-coder",
    api_base="http://localhost:8080/v1",
    api_key="not-needed"
)
```

### Using Python

```python
from openai import OpenAI

client = OpenAI(
    api_key="not-needed",
    base_url="http://localhost:8080/v1"
)

response = client.chat.completions.create(
    model="qwen3-coder",
    messages=[{"role": "user", "content": "Hello!"}]
)

print(response.choices[0].message.content)
```

## Performance Optimization

### GPU Layers

```bash
# Use all GPU layers
-ngl 999

# Or limit for smaller VRAM
-ngl 32
```

### Context Size

```bash
# Smaller context = faster
-c 2048

# Larger context = more memory
-c 8192
```

### Thread Optimization

```bash
# Use all CPU cores
-t $(nproc)

# Or limit
-t 8
```

### Batch Processing

```bash
# Enable continuous batching
--cont-batching

# Set batch size
--batch-size 512
```

## Service Management

### Systemd Service

```bash
sudo tee /etc/systemd/system/llama-server.service << 'EOF'
[Unit]
Description=llama.cpp Server
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/home/sergiok
ExecStart=/usr/local/bin/llama-server -m /home/sergiok/unsloth/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-UD-Q4_K_XL.gguf -ngl 999 -c 4096 -port 8080 --host 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable llama-server
sudo systemctl start llama-server
```

### Check Status

```bash
systemctl status llama-server
journalctl -u llama-server -f
```

## Troubleshooting

### Out of Memory

```bash
# Reduce GPU layers
-ngl 32

# Reduce context
-c 1024

# Use smaller model
-m smaller-model.gguf
```

### Slow Inference

```bash
# Use more threads
-t 12

# Enable GPU
-ngl 999

# Use quantized model (Q4_K_XL is already optimized)
```

### Connection Refused

```bash
# Check if server is running
ps aux | grep llama-server

# Check port
netstat -tlnp | grep 8080
```

## Next Steps

- [Ollama Integration](./08-ollama-integration.md)
- [VS Code Integration](./09-vscode-integration.md)
- [Model Selection](./10-model-selection.md)
