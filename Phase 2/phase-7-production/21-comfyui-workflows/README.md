# Part 25: ComfyUI + Ollama Local Workflows

## Overview

This section covers running ComfyUI with local Ollama integration for AI-powered image and video generation workflows on your Jetson AGX Orin 64GB. Create automated pipelines that combine text generation (Ollama) with image/video generation (ComfyUI).

## Available Guides

| File | Description |
|------|-------------|
| [01-overview.md](./01-overview.md) | ComfyUI + Ollama workflow introduction |
| [02-comfyui-setup.md](./02-comfyui-setup.md) | ComfyUI installation on Jetson |
| [03-ollama-integration.md](./03-ollama-integration.md) | Connecting Ollama to ComfyUI |
| [04-workflow-basics.md](./04-workflow-basics.md) | Basic workflow creation |
| [05-image-generation.md](./05-image-generation.md) | Automated image generation |
| [06-video-generation.md](./06-video-generation.md) | Video generation workflows |
| [07-api-automation.md](./07-api-automation.md) | API-based automation |
| [08-custom-nodes.md](./08-custom-nodes.md) | Creating custom ComfyUI nodes |
| [09-performance.md](./09-performance.md) | Jetson optimization |
| [10-troubleshooting.md](./10-troubleshooting.md) | Common issues |

## Quick Start

```bash
# 1. Install ComfyUI (see guide)
# 2. Install Ollama integration nodes
# 3. Create workflow
# 4. Run via API
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Jetson AGX Orin                        │
│                                                             │
│  ┌──────────────┐           ┌──────────────┐              │
│  │    Ollama    │◀────────▶│   ComfyUI    │              │
│  │  (Text/LLM)  │   API    │ (Image/Video)│              │
│  └──────────────┘           └──────────────┘              │
│         │                          │                        │
│         ▼                          ▼                        │
│  ┌──────────────────────────────────────────┐            │
│  │         Automated Workflows                │            │
│  │  Text Prompt → Ollama → ComfyUI → Image   │            │
│  └──────────────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Jetson AGX Orin 64GB
- JetPack 6.2.2
- Ollama running with models
- 16GB+ RAM available

## Next Steps

Start with [01-overview.md](./01-overview.md) to understand the workflow architecture.
