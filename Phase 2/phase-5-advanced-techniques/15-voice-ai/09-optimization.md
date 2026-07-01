# Speech AI Optimization on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [System Optimization](#system-optimization)
3. [STT Optimization](#stt-optimization)
4. [TTS Optimization](#tts-optimization)
5. [Memory Management](#memory-management)

## Introduction

Optimize speech AI performance on Jetson AGX Orin.

## System Optimization

```bash
# Maximum performance
sudo nvpmodel -m 0
sudo jetson_clocks
```

## STT Optimization

### Model Selection

```python
# Use smaller models for speed
stt = SpeechToText("tiny")  # Fastest
# or
stt = SpeechToText("base")  # Balance
```

### Compute Type

```python
# Use float16 for CUDA
model = WhisperModel("base", compute_type="float16")

# Use int8 for CPU
model = WhisperModel("base", compute_type="int8")
```

## TTS Optimization

### Use Piper

```bash
# Piper is fastest for Jetson
# Use smaller voice models
voice = "en_US-lessac"  # 39MB
# vs
voice = "en_US-lessac-large"  # 317MB
```

## Memory Management

```python
# Clear memory between operations
import torch

torch.cuda.empty_cache()
```

## Next Steps

- [Troubleshooting](./10-troubleshooting.md) - Fix issues
- [API Reference](./11-api-reference.md) - Full API
