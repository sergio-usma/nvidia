# Troubleshooting

## Table of Contents

1. [Connection Issues](#connection-issues)
2. [Model Issues](#model-issues)
3. [Memory Issues](#memory-issues)
4. [Performance Issues](#performance-issues)
5. [Tool-Specific Issues](#tool-specific-issues)

## Connection Issues

### Ollama Not Running

```bash
# Check if Ollama is running
ps aux | grep ollama

# Start Ollama
ollama serve

# Or as service
sudo systemctl start ollama

# Check logs
journalctl -u ollama -f
```

### Connection Refused

```bash
# Verify port is open
curl http://localhost:11434/api/tags

# Check firewall
sudo ufw status
sudo ufw allow 11434/tcp

# Verify listening
netstat -tlnp | grep 11434
```

### llama.cpp Server Not Starting

```bash
# Check CUDA availability
nvcc --version

# Try without GPU
./llama-server -m model.gguf -ngl 0

# Check logs
./llama-server -m model.gguf 2>&1 | head -20
```

## Model Issues

### Model Not Found

```bash
# List available models
ollama list

# Pull required model
ollama pull qwen2.5-coder:latest

# Or with specific version
ollama pull qwen2.5-coder:7b
```

### Wrong Model Output

```bash
# Check model is correct
ollama list

# Use specific model in request
curl http://localhost:11434/v1/chat/completions \
  -d '{"model": "qwen2.5-coder:latest", ...}'
```

### Model Loading Slow

```bash
# Check disk speed
hdparm -t /dev/nvme0n1

# Use SSD for models
ln -s /path/to/nvme/models ~/.ollama/models
```

## Memory Issues

### Out of Memory

```bash
# Check available memory
free -h

# Kill unused processes
pkill -9 chrome

# Use smaller model
ollama pull qwen2.5-coder:7b
```

### GPU Out of Memory

```bash
# Check GPU memory
tegrastats

# Reduce GPU layers
-ngl 32

# Use quantized model
# (Q4_K_XL is already optimized)
```

### llama.cpp Memory Issues

```bash
# Reduce context
-c 1024

# Don't use GPU
-ngl 0

# Disable memory map
--no-mmap
```

## Performance Issues

### Slow Inference

```bash
# Check system resources
htop
tegrastats

# Enable max performance
sudo nvpmodel -m 0
sudo jetson_clocks

# Use GPU
-ngl 999

# More threads
-t 12
```

### High Latency

```bash
# Test local latency
ping localhost

# Check network
curl -w "%{time_total}s" http://localhost:11434/api/tags

# Reduce context
# (smaller context = faster)
```

### Thermal Throttling

```bash
# Check temperature
tegrastats

# Improve cooling
# - Clean heatsink
# - Add fan
# - Reduce ambient temperature
```

## Tool-Specific Issues

### OpenCode Issues

```bash
# Check config
cat ~/.config/opencode/config.yaml

# Verify model path
ls -la ~/.ollama/models/

# Update OpenCode
pip3 install --upgrade opencode
```

### Continue.dev Issues

```bash
# Check Python version
python3 --version

# Install dependencies
pip3 install continuedev

# Check config
cat ~/.continue/config.py
```

### VS Code SSH Issues

```bash
# Test SSH connection
ssh -v sergiok@jetson-ip

# Check VS Code logs
View → Output → Remote - SSH

# Reinstall extension
Ctrl+Shift+P → Extensions: Uninstall → Install
```

## Common Error Messages

### "model not found"

```
# Fix: Pull model
ollama pull qwen2.5-coder:latest
```

### "connection refused"

```
# Fix: Start service
ollama serve
```

### "out of memory"

```
# Fix: Use smaller model or reduce context
ollama pull qwen2.5-coder:7b
```

### "CUDA error"

```
# Fix: Disable CUDA
-ngl 0
```

### "timeout"

```
# Fix: Increase timeout or use smaller model
```

## Debugging Tips

### Test API Directly

```bash
# Test Ollama API
curl http://localhost:11434/api/tags

# Test chat
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder:latest","messages":[{"role":"user","content":"hi"}]}'
```

### Check Logs

```bash
# Ollama logs
journalctl -u ollama -f

# System logs
dmesg | tail

# Tool logs
# Check individual tool documentation
```

### Test Different Backends

```bash
# Try Ollama
ollama run qwen2.5-coder

# Try llama.cpp
./llama-cli -m model.gguf -ngl 999

# Compare performance
```

## Getting Help

- [Ollama docs](https://github.com/ollama/ollama)
- [llama.cpp docs](https://github.com/ggerganov/llama.cpp)
- [Continue.dev docs](https://continue.dev/docs)
- [NVIDIA Jetson Forum](https://forums.developer.nvidia.com/c/agx/)
