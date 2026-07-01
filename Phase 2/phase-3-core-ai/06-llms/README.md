# LLMs on Jetson AGX Orin

This section covers running Large Language Models on your Jetson AGX Orin.

## Available Guides

### 01: Ollama Setup
- [Ollama Installation](01-ollama-setup.md) - Easiest way to run LLMs
- Quick start with `ollama pull` and `ollama run`
- Model management and optimization

### 02: llama.cpp
- [llama.cpp Installation](02-llama-cpp.md) - Compile from source with CUDA
- Running GGUF models directly
- Performance tuning for Jetson

### 03: Model Management
- [Model Management](03-model-management.md) - Managing storage and models
- Swap configuration for large models
- Finding and downloading models

### 04: API Servers
- [LLM API Servers](04-llm-api-servers.md) - Expose models via API
- Open WebUI integration
- Custom API endpoints

## Quick Start

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start service
sudo systemctl start ollama
sudo systemctl enable ollama

# Download a model
ollama pull llama3.2

# Run interactively
ollama run llama3.2
```

## Performance Tips

- Use MAXN mode: `sudo nvpmodel -m 0 && sudo jetson_clocks`
- Monitor with: `tegrastats` or `jtop`
- Use quantized models (Q4, Q5) for better performance

## Related Resources

See the `/home/sergiok/Desktop/JETSON-CONFIG/Tutorial/` folder for additional detailed guides in Spanish:
- `jetson_orin_llm_setup.md` - Complete Ollama guide
- `install_models_via_cpp.md` - llama.cpp detailed tutorial
- `guia_gestion_modelos_ia.md` - Model management guide
