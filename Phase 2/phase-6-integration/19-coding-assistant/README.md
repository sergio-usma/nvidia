# Part 22: Local AI Coding Tools Integration

## Overview

This section covers integrating AI coding assistants (Claude Code, Codex, OpenCode, OpenClaw) with your Jetson AGX Orin 64GB for local AI-powered software development.

## Available Guides

| File | Description |
|------|-------------|
| [01-overview.md](./01-overview.md) | Introduction to local AI coding tools |
| [02-environment-setup.md](./02-environment-setup.md) | Prerequisites and environment configuration |
| [03-claude-code-setup.md](./03-claude-code-setup.md) | Claude Code installation and configuration |
| [04-codex-integration.md](./04-codex-integration.md) | OpenAI Codex/local alternatives setup |
| [05-opencode-setup.md](./05-opencode-setup.md) | OpenCode installation and usage |
| [06-openclaw-setup.md](./06-openclaw-setup.md) | OpenClaw setup guide |
| [07-llama.cpp-integration.md](./07-llama.cpp-integration.md) | Connect tools to llama.cpp models |
| [08-ollama-integration.md](./08-ollama-integration.md) | Connect tools to Ollama models |
| [09-vscode-integration.md](./09-vscode-integration.md) | VS Code remote development setup |
| [10-model-selection.md](./10-model-selection.md) | Choosing the right model for coding |
| [11-custom-prompts.md](./11-custom-prompts.md) | Custom prompts and workflows |
| [12-performance.md](./12-performance.md) | Optimization for Jetson |
| [13-troubleshooting.md](./13-troubleshooting.md) | Common issues and solutions |

## Quick Start

```bash
# 1. Install OpenCode (recommended for Jetson)
curl -sSL https://opencode.ai/install | sh

# 2. Configure with local Ollama
opencode config set provider ollama
opencode config set model qwen2.5-coder:latest

# 3. Or use with llama.cpp
opencode config set provider llama.cpp
opencode config set model ./models/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-UD-Q4_K_XL.gguf
```

## Prerequisites

- Jetson AGX Orin 64GB
- JetPack 6.2.2
- VS Code or JetBrains Gateway for remote development
- Ollama or llama.cpp with coding models

## Compatible Models

### Ollama Models
- `qwen2.5-coder:latest` - Specialized coding
- `codeqwen:latest` - Code generation
- `granite3.3:latest` - Enterprise coding
- `qwen3-coder:latest` - Advanced code generation
- `deepseek-r1:8b` - Reasoning tasks

### llama.cpp Models
- `Qwen3-Coder-Next-GGUF` - High-quality coding
- `Qwen3.5-27B-GGUF` - General purpose
- `GLM-4.7-Flash-GGUF` - Fast inference

## Next Steps

Start with [01-overview.md](./01-overview.md) to understand the available tools.
