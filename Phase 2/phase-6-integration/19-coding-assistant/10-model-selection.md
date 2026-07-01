# Model Selection Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Coding Models](#coding-models)
3. [General Models](#general-models)
4. [Specialized Models](#specialized-models)
5. [Performance Comparison](#performance-comparison)

## Introduction

Choosing the right model for your Jetson AGX Orin depends on your use case, available RAM, and performance requirements.

## Coding Models

### Recommended: Qwen2.5-Coder

```bash
# Best overall for coding
ollama pull qwen2.5-coder:latest
ollama pull qwen2.5-coder:14b

# Smaller, faster version
ollama pull qwen2.5-coder:7b
```

| Version | Size | Memory | Speed | Quality |
|---------|------|--------|-------|---------|
| 7B | ~4GB | ~8GB | Fast | Good |
| 14B | ~8GB | ~16GB | Medium | Very Good |
| 32B | ~18GB | ~24GB | Slow | Excellent |

### CodeQwen

```bash
# Good for code generation
ollama pull codeqwen:latest
ollama pull codeqwen:7b
```

### Qwen3-Coder

```bash
# Advanced coding capabilities
ollama pull qwen3-coder:latest
ollama pull qwen3-coder:8b
```

### Granite-3.3

```bash
# Enterprise-focused
ollama pull granite3.3:latest
```

## General Models

### Llama 3.2

```bash
# Good general purpose
ollama pull llama3.2:3b
ollama pull llama3.2:1b
```

### Mistral

```bash
# Fast, versatile
ollama pull mistral:latest
ollama pull mistral-nemo:latest
```

### Qwen 2.5

```bash
# General chat
ollama pull qwen2.5:latest
ollama pull qwen2.5:14b
```

## Specialized Models

### DeepSeek-R1 (Reasoning)

```bash
# Mathematical reasoning
ollama pull deepseek-r1:8b
ollama pull deepseek-r1:14b
ollama pull deepseek-r1:32b
```

Best for:
- Complex logic problems
- Math computations
- Chain-of-thought tasks

### Embedding Models

```bash
# For RAG applications
ollama pull nomic-embed-text:latest
ollama pull embeddinggemma:latest
```

## Your Installed Models

### llama.cpp Models

| Model | Purpose | Command |
|-------|---------|---------|
| Qwen3-Coder-Next | AI Dev/Coding | llama-cli -m ~/unsloth/Qwen3-Coder-Next-GGUF/... -ngl 999 -c 4096 |
| Qwen3.5-27B | General/Llama.cpp | llama-cli -m ~/.cache/llama.cpp/... -ngl 999 -c 4096 |
| GLM-4.7-Flash | Speed/Chat | llama-cli -m ~/unsloth/GLM-4.7-Flash-GGUF/... -ngl 999 -c 4096 |
| Nemotron-120B | High-End | llama-cli -m ~/Nemotron-Super-GGUF/... -ngl 999 -c 2048 |

### Ollama Models

| Model | Best For | Command |
|-------|----------|---------|
| deepscaler | Math reasoning | ollama pull deepscaler |
| tinyllama | Edge devices | ollama pull tinyllama |
| openthinker | Reasoning | ollama pull openthinker |
| codeqwen | Code generation | ollama pull codeqwen |
| mathstral | Math | ollama pull mathstral |
| mistral | General | ollama pull mistral |
| mistral-nemo | Multilingual | ollama pull mistral-nemo |
| mistrallite | Lightweight | ollama pull mistrallite |
| opencoder | Code completion | ollama pull opencoder |
| qwen2.5-coder | Coding | ollama pull qwen2.5-coder |
| granite3.3 | Enterprise | ollama pull granite3.3 |
| phi4-mini-reasoning | Quick reasoning | ollama pull phi4-mini-reasoning |
| lfm2.5-thinking | Chain-of-thought | ollama pull lfm2.5-thinking |
| qwen3-coder | Advanced coding | ollama pull qwen3-coder |
| nemotron-3-nano | Nano tasks | ollama pull nemotron-3-nano |
| lfm2 | General | ollama pull lfm2 |
| glm-4.7-flash | Fast chat | ollama pull glm-4.7-flash |
| deepseek-r1:8b | Reasoning | ollama pull deepseek-r1:8b |
| gpt-oss | Broad tasks | ollama pull gpt-oss |

## Performance Comparison

### Coding Tasks

| Model | MBPP | HumanEval | Speed |
|-------|------|-----------|-------|
| Qwen2.5-Coder | High | High | Medium |
| CodeQwen | High | High | Fast |
| Granite-3.3 | Medium | Medium | Medium |
| DeepSeek-R1 | Very High | High | Slow |

### General Tasks

| Model | MMLU | Speed | Memory |
|-------|------|-------|--------|
| Mistral | 71% | Fast | 4GB |
| Llama3.2 | 69% | Fast | 2GB |
| Qwen2.5 | 72% | Medium | 4GB |

## Selection Guide

### By Use Case

| Use Case | Recommended Model |
|----------|------------------|
| General coding | qwen2.5-coder:latest |
| Code completion | codeqwen:latest |
| Complex reasoning | deepseek-r1:8b |
| Fast prototyping | mistral:latest |
| Enterprise/IBM | granite3.3:latest |
| Multiple languages | qwen3-coder:latest |

### By Available Memory

| RAM Available | Recommended Model |
|--------------|-------------------|
| 8GB | tinyllama, mistrallite |
| 16GB | qwen2.5-coder:7b, codeqwen:7b |
| 32GB | qwen2.5-coder:14b, qwen3-coder |
| 64GB | qwen2.5-coder:32b, deepseek-r1:32b |

### By Speed

| Priority | Model |
|----------|-------|
| Fastest | tinyllama, mistrallite |
| Fast | codeqwen, qwen2.5-coder:7b |
| Medium | mistral, llama3.2 |
| Quality | qwen2.5-coder:14b, deepseek-r1 |

## Switching Models

### For Different Tasks

```bash
# Fast coding
ollama run qwen2.5-coder:7b

# Quality coding
ollama run qwen2.5-coder:14b

# Reasoning
ollama run deepseek-r1:8b

# General chat
ollama run mistral
```

### In Tools

```bash
# OpenCode
opencode --model qwen2.5-coder:14b

# Aider
aider --model ollama/qwen2.5-coder:14b
```

## Next Steps

- [Custom Prompts](./11-custom-prompts.md)
- [Performance Optimization](./12-performance.md)
