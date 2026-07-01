# MCP Tools Integration on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [AI Tool Tools](#ai-tool-tools)
3. [Hardware Tools](#hardware-tools)
4. [File Tools](#file-tools)

## Introduction

Integrate various AI tools with MCP on Jetson.

## AI Tool Tools

### Image Generation

```python
Tool(
    name="generate_image",
    description="Generate image using Stable Diffusion",
    inputSchema={
        "type": "object",
        "properties": {
            "prompt": {"type": "string"},
            "negative_prompt": {"type": "string"},
            "steps": {"type": "number", "default": 30}
        },
        "required": ["prompt"]
    }
)
```

### Speech Processing

```python
Tool(
    name="speech_to_text",
    description="Transcribe audio using Whisper",
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
    description="Generate speech using Piper TTS",
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

### GPIO Control

```python
Tool(
    name="gpio_write",
    description="Write to GPIO pin",
    inputSchema={
        "type": "object",
        "properties": {
            "pin": {"type": "number"},
            "value": {"type": "number"}
        },
        "required": ["pin", "value"]
    }
)

Tool(
    name="read_sensor",
    description="Read sensor data",
    inputSchema={
        "type": "object",
        "properties": {
            "sensor": {"type": "string"}
        },
        "required": ["sensor"]
    }
)
```

## File Tools

### File Operations

```python
Tool(
    name="list_directory",
    description="List directory contents",
    inputSchema={
        "type": "object",
        "properties": {
            "path": {"type": "string"}
        },
        "required": ["path"]
    }
)

Tool(
    name="search_files",
    description="Search for files",
    inputSchema={
        "type": "object",
        "properties": {
            "directory": {"type": "string"},
            "pattern": {"type": "string"}
        },
        "required": ["directory", "pattern"]
    }
)
```

## Next Steps

- [Jetson Tools](./09-jetson-tools.md)
- [Ollama Integration](./10-ollama-integration.md)
