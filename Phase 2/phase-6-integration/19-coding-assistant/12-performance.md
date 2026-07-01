# Performance Optimization

## Table of Contents

1. [Introduction](#introduction)
2. [System Optimization](#system-optimization)
3. [Model Optimization](#model-optimization)
4. [Tool Optimization](#tool-optimization)
5. [Monitoring](#monitoring)

## Introduction

Optimize AI coding tools for best performance on Jetson AGX Orin.

## System Optimization

### Enable Max Performance

```bash
# Max performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Verify
nvpmodel -q
jetson_clocks --show
```

### CPU Optimization

```bash
# Set CPU governor to performance
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Or use interactive
echo interactive | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

### Memory Management

```bash
# Clear memory
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches

# Monitor
free -h
```

### GPU Configuration

```bash
# Check GPU status
tegrastats

# Monitor with jtop
sudo pip3 install jtop
sudo jtop
```

## Model Optimization

### Use Quantized Models

```bash
# Prefer Q4_K_XL models (already optimized)
# Q4_K_XL = Q4_K_M + Q6_K mix

# Smaller quantized versions
ollama pull qwen2.5-coder:7b  # 7B > 14B > 32B
```

### Reduce Context Size

```python
# Reduce in API call
response = requests.post(
    "http://localhost:11434/v1/chat/completions",
    json={
        "model": "qwen2.5-coder:latest",
        "messages": [...],
        "options": {
            "num_ctx": 2048  # Reduce from default 4096
        }
    }
)
```

### Limit Response Length

```python
# Limit max tokens
response = requests.post(
    "http://localhost:11434/v1/chat/completions",
    json={
        "model": "qwen2.5-coder:latest",
        "messages": [...],
        "options": {
            "num_predict": 512  # Limit response
        }
    }
)
```

### Temperature Tuning

```python
# Lower temperature for faster, focused responses
response = requests.post(
    "http://localhost:11434/v1/chat/completions",
    json={
        "model": "qwen2.5-coder:latest",
        "messages": [...],
        "options": {
            "temperature": 0.3  # Lower = faster
        }
    }
)
```

## Tool Optimization

### OpenCode Optimization

```yaml
# ~/.config/opencode/config.yaml
# Use smaller model for speed
model: qwen2.5-coder:7b

# Reduce context
context_size: 2048

# Limit tokens
max_tokens: 1024
```

### llama.cpp Optimization

```bash
# Use GPU layers
-ngl 999

# Limit threads
-t 8

# Use smaller context
-c 2048

# Enable batch processing
--cont-batching
--batch-size 512
```

### Aider Optimization

```bash
# Use smaller model
aider --model qwen2.5-coder:7b

# Low latency mode
aider --just-model-update --no-auto-commit
```

## Monitoring

### Resource Usage

```bash
# CPU/Memory
htop

# GPU
tegrastats

# Or jtop
sudo jtop
```

### API Latency

```python
import time

def timed_request():
    start = time.time()
    response = requests.post(
        "http://localhost:11434/v1/chat/completions",
        json={
            "model": "qwen2.5-coder:latest",
            "messages": [{"role": "user", "content": "Hi"}]
        }
    )
    elapsed = time.time() - start
    print(f"Latency: {elapsed:.2f}s")
    return response
```

### Benchmark Script

```python
# benchmark.py
import requests
import time

def benchmark(model, num_requests=10):
    times = []
    
    for i in range(num_requests):
        start = time.time()
        response = requests.post(
            "http://localhost:11434/v1/chat/completions",
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Write a function"}],
                "options": {"num_predict": 100}
            }
        )
        times.append(time.time() - start)
    
    avg = sum(times) / len(times)
    print(f"{model}: avg={avg:.2f}s, min={min(times):.2f}s, max={max(times):.2f}s")

# Run
benchmark("qwen2.5-coder:7b")
benchmark("qwen2.5-coder:14b")
```

## Performance Checklist

- [ ] Enable max performance mode
- [ ] Use GPU acceleration
- [ ] Choose appropriate model size
- [ ] Limit context window
- [ ] Limit response tokens
- [ ] Use quantized models
- [ ] Monitor resource usage
- [ ] Use SSD for model files

## Recommended Configurations

### Fast Development

```yaml
model: qwen2.5-coder:7b
context_size: 2048
max_tokens: 512
temperature: 0.3
```

### Quality Development

```yaml
model: qwen2.5-coder:14b
context_size: 4096
max_tokens: 2048
temperature: 0.7
```

### Quick Interactions

```yaml
model: mistral:latest
context_size: 1024
max_tokens: 256
temperature: 0.5
```

## Next Steps

- [Troubleshooting](./13-troubleshooting.md)
