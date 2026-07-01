# Jetson Tools for MCP on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [System Tools](#system-tools)
3. [AI Tools](#ai-tools)
4. [Hardware Tools](#hardware-tools)

## Introduction

Jetson-specific MCP tools.

## System Tools

```python
# System monitoring
Tool(
    name="system_monitor",
    description="Get system monitoring data",
    inputSchema={"type": "object", "properties": {}}
)

Tool(
    name="check_gpu",
    description="Check GPU status",
    inputSchema={"type": "object", "properties": {}}
)

Tool(
    name="check_temperature",
    description="Check CPU/GPU temperature",
    inputSchema={"type": "object", "properties": {}}
)
```

## AI Tools

```python
# Image generation
Tool(
    name="generate_image",
    description="Generate image with Stable Diffusion",
    inputSchema={
        "type": "object",
        "properties": {
            "prompt": {"type": "string"},
            "model": {"type": "string"}
        },
        "required": ["prompt"]
    }
)

# Speech tools
Tool(
    name="speech_to_text",
    description="Transcribe audio",
    inputSchema={
        "type": "object", 
        "properties": {
            "audio_path": {"type": "string"}
        },
        "required": ["audio_path"]
    }
)

Tool(
    name="text_to_speech",
    description="Generate speech",
    inputSchema={
        "type": "object",
        "properties": {
            "text": {"type": "string"},
            "voice": {"type": "string"}
        },
        "required": ["text"]
    }
)
```

## Hardware Tools

```python
# GPIO
Tool(
    name="gpio_control",
    description="Control GPIO pins",
    inputSchema={
        "type": "object",
        "properties": {
            "pin": {"type": "number"},
            "mode": {"type": "string"},
            "value": {"type": "number"}
        }
    }
)

# Camera
Tool(
    name="capture_image",
    description="Capture image from camera",
    inputSchema={
        "type": "object",
        "properties": {
            "device": {"type": "number", "default": 0}
        }
    }
)
```

## Next Steps

- [Ollama Integration](./10-ollama-integration.md)
- [Security](./11-security.md)
