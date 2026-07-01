# Ollama Setup

Ollama is the easiest way to run LLMs locally. It handles model downloading and provides a REST API.

## Install Ollama

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

This installs Ollama as a **systemd service** that starts automatically at boot.

## Verify Installation

```bash
ollama --version
```

## Control Ollama Service

### Start/Stop/Restart

```bash
sudo systemctl start ollama
sudo systemctl stop ollama
sudo systemctl restart ollama
```

### Disable Auto-start

If you don't want Ollama to start on boot:

```bash
sudo systemctl disable ollama
```

You can still start it manually with `ollama serve` when needed.

## Pull a Model

Example models (choose based on your RAM):

| Model | Size | Use Case |
|-------|------|----------|
| tinyllama | ~1GB | Testing |
| llama3.2 | ~4GB | General |
| qwen2.5-coder:7b | ~4GB | Coding |
| deepseek-r1:14b | ~9GB | Reasoning |
| gemma3:27b | ~18GB | Large |

```bash
ollama pull llama3.2
```

## Run Interactively

```bash
ollama run llama3.2
```

Type `/bye` to exit.

## Serve API

Ollama's service runs on port 11434. Test it:

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Hello, how are you?",
  "stream": false
}'
```

## Configure Network Access

By default, Ollama only listens on localhost. To access from other machines:

```bash
sudo systemctl edit ollama.service
```

Add:

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"
```

Reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart ollama
```

## Persistence

Models are stored in:
- `/usr/share/ollama/.ollama/models` (if run as service)
- `~/.ollama/models` (if run manually)

To move models to a different location:

```bash
sudo systemctl stop ollama
sudo mv /usr/share/ollama/.ollama/models /path/to/new/location
sudo ln -s /path/to/new/location /usr/share/ollama/.ollama/models
sudo systemctl start ollama
```

## Recommended Models

For your 64GB Jetson:

- **Coding**: `qwen2.5-coder:7b`, `qwen2.5-coder:14b`
- **Reasoning**: `deepseek-r1:14b`, `deepseek-r1:32b`
- **General**: `llama3.2`, `mistral`
- **Vision**: `llava`, `minicpm-v:8b`

## Next Steps

- [llama.cpp Setup](02-llama-cpp.md) - More control over models
- [MLC-LLM](03-mlc-llm.md) - Maximum performance
- [Model Management](04-model-management.md) - Organize your models
