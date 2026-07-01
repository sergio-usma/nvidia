# MCP Resources on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [System Resources](#system-resources)
3. [AI Model Resources](#ai-model-resources)
4. [Custom Resources](#custom-resources)

## Introduction

Expose Jetson resources via MCP.

## System Resources

```python
Resource(
    uri="jetson://cpu",
    name="cpu_info",
    description="CPU information and usage",
    mimeType="application/json"
)

Resource(
    uri="jetson://memory", 
    name="memory_info",
    description="Memory usage",
    mimeType="application/json"
)

Resource(
    uri="jetson://disk",
    name="disk_info",
    description="Disk usage",
    mimeType="application/json"
)
```

## AI Model Resources

```python
Resource(
    uri="jetson://ollama/models",
    name="ollama_models",
    description="Available Ollama models",
    mimeType="application/json"
)

Resource(
    uri="jetson://whisper/status",
    name="whisper_models",
    description="Whisper models",
    mimeType="application/json"
)
```

## Custom Resources

```python
# Document resources
Resource(
    uri="file:///home/jetson/docs",
    name="documentation",
    description="Local documentation",
    mimeType="text/markdown"
)
```

## Next Steps

- [Prompts](./08-prompts.md)
- [Jetson Tools](./09-jetson-tools.md)
