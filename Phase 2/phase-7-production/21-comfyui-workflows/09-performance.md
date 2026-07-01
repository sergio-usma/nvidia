# Performance Optimization

## Jetson Optimization

### Enable Max Performance

```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

### Memory Management

```python
# Monitor memory
import psutil

def check_memory():
    mem = psutil.virtual_memory()
    if mem.percent > 90:
        # Reduce batch size or wait
        pass
```

### Reduce Resolution

```python
# Use smaller resolutions
workflow = {
    "1": {"inputs": {"width": 512, "height": 512}, "class_type": "EmptyLatentImage"},
    # Instead of 1024x1024
}
```

## ComfyUI Optimization

### Use Smaller Models

```bash
# Use SD 1.5 instead of SDXL
# Use quantized models
```

### Reduce Steps

```python
# Reduce sampling steps
"steps": 15,  # instead of 30
```

### Enable VRAM Optimization

```python
# In ComfyUI settings:
# - Enable "Low VRAM" mode
# - Disable preview
# - Use CPU for VAE
```

## Ollama Optimization

### Use Smaller Models

```python
# Instead of llama3.2:3b
model = "tinyllama"  # For prompt generation only
```

### Cache Prompts

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_prompt(concept):
    return generate_prompt(concept)
```

## Next Steps

- [Troubleshooting](./10-troubleshooting.md) - Common issues
