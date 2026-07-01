# Video Processing Optimization on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [System Optimization](#system-optimization)
3. [Memory Management](#memory-management)
4. [Performance Tips](#performance-tips)

## Introduction

Optimize video processing on Jetson AGX Orin for best performance.

## System Optimization

```bash
# Maximum performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Check thermal status
tegrastats --interval 1000

# Monitor GPU usage
tegrastats
```

## Memory Management

```python
import torch

# Clear memory between frames
def process_with_memory_management(pipeline, frames):
    """Process frames with memory management"""
    
    results = []
    
    for i, frame in enumerate(frames):
        # Process
        result = pipeline(frame)
        results.append(result)
        
        # Clear memory every N frames
        if i > 0 and i % 3 == 0:
            torch.cuda.empty_cache()
    
    return results
```

## Performance Tips

### Resolution Tradeoffs

| Resolution | Speed | Quality |
|------------|-------|---------|
| 256x256 | Fast | Low |
| 384x384 | Medium | Medium |
| 512x512 | Slow | High |

### Settings for Speed

```python
# Fast generation settings
FAST_SETTINGS = {
    "height": 384,
    "width": 384,
    "num_inference_steps": 15,
    "guidance_scale": 1.0,
}
```

### Settings for Quality

```python
# Quality settings
QUALITY_SETTINGS = {
    "height": 512,
    "width": 512,
    "num_inference_steps": 30,
    "guidance_scale": 7.5,
}
```

## Next Steps

- [Troubleshooting](./13-troubleshooting.md) - Fix issues
