# Local AI Coding Tools Overview

## Table of Contents

1. [What are AI Coding Tools](#what-are-ai-coding-tools)
2. [Available Tools](#available-tools)
3. [Tool Comparison](#tool-comparison)
4. [Architecture Overview](#architecture-overview)

## What are AI Coding Tools

AI coding tools are intelligent assistants that help developers write, debug, and refactor code. Unlike cloud-based solutions, local tools run entirely on your Jetson AGX Orin, providing:

- **Privacy**: Code never leaves your device
- **Offline capability**: Work without internet
- **No API costs**: Free to use after initial setup
- **Customization**: Full control over models and prompts
- **Latency**: Faster responses with local inference

## Available Tools

### Claude Code (claude.ai/code)

Claude Code is Anthropic's CLI tool for AI-assisted coding. It provides:
- Terminal-based AI assistant
- Git integration
- File editing capabilities
- Multi-file context awareness

**Note**: Claude Code requires an API connection to Anthropic. For fully local operation, use OpenCode or similar open alternatives.

### OpenCode

OpenCode is an open-source AI coding assistant that can run locally. Features:
- Local model support (llama.cpp, Ollama)
- VS Code integration
- File editing and creation
- Git-aware context
- Terminal integration

### OpenClaw

OpenClaw is another open alternative focused on:
- Lightweight operation
- Multiple backend support
- CLI and IDE integration

### Codex / Codex CLI

OpenAI's Codex powers GitHub Copilot. For local use:
- Use open alternatives like CodeQwen
- Connect to local Ollama/llama.cpp
- VS Code extensions available

### Other Options

| Tool | Type | Local Support |
|------|------|---------------|
| Continue.dev | VS Code extension | Yes (local models) |
| Zed | Editor with AI | Partial |
| Cursor | IDE with AI | API only |
| Aider | CLI editor | Yes (local) |

## Tool Comparison

| Feature | Claude Code | OpenCode | OpenClaw | Aider |
|---------|-------------|----------|----------|-------|
| Local Models | Via API | Full | Full | Full |
| VS Code | No | Yes | Limited | No |
| CLI Only | Yes | Yes | Yes | Yes |
| Git Integration | Yes | Yes | Basic | Yes |
| ARM64 Support | Via API | Yes | Yes | Yes |
| Cost | API only | Free | Free | Free |

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Jetson AGX Orin                         │
│                                                             │
│  ┌──────────────┐    ┌──────────────┐    ┌─────────────┐ │
│  │ Claude Code  │    │   OpenCode   │    │  OpenClaw   │ │
│  │   (CLI)      │    │   (CLI/IDE)  │    │   (CLI)     │ │
│  └──────┬───────┘    └──────┬───────┘    └──────┬──────┘ │
│         │                    │                    │        │
│         ▼                    ▼                    ▼        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Model Layer (One of below)              │  │
│  │                                                       │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │  │
│  │  │   Ollama    │  │  llama.cpp  │  │  OpenAI   │  │  │
│  │  │  (REST)     │  │  (CLI)      │  │  Compatible│  │  │
│  │  └─────────────┘  └─────────────┘  └────────────┘  │  │
│  └──────────────────────────────────────────────────────┘  │
│                           │                                 │
│                           ▼                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              Local Models (GGUF/GGML)                │  │
│  │                                                       │  │
│  │  • Qwen2.5-Coder  • CodeQwen   • Granite 3.3        │  │
│  │  • Qwen3-Coder    • DeepSeek-R1 • Llama variants    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Model Selection by Task

### Code Generation
- **Ollama**: `qwen2.5-coder:latest`, `codeqwen:latest`
- **llama.cpp**: Qwen3-Coder-Next-GGUF

### Code Review
- **Ollama**: `granite3.3:latest`, `qwen3-coder:latest`
- **llama.cpp**: Qwen3.5-27B-GGUF

### Debugging
- **Ollama**: `deepseek-r1:8b`, `qwen2.5-coder:latest`
- **llama.cpp**: Qwen3-Coder-Next-GGUF

### General Programming
- **Ollama**: `mistral:latest`, `mistral-nemo:latest`
- **llama.cpp**: GLM-4.7-Flash-GGUF

## Installation Path

1. [Environment Setup](./02-environment-setup.md) - Prepare your system
2. [OpenCode Setup](./05-opencode-setup.md) - Install primary tool
3. [Model Selection](./10-model-selection.md) - Choose your models
4. [VS Code Integration](./09-vscode-integration.md) - Connect to IDE

## Next Steps

Continue to [Environment Setup](./02-environment-setup.md) to prepare your Jetson.
