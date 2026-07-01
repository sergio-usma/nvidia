# Part 16: Fine-Tuning LLMs on Jetson AGX Orin

A comprehensive guide to fine-tuning Large Language Models locally on your NVIDIA Jetson AGX Orin 64GB for custom tasks and domain-specific applications.

## Table of Contents

1. [Overview](./01-overview.md) - Introduction to fine-tuning concepts
2. [Environment Setup](./02-environment-setup.md) - Prerequisites and dependencies
3. [Alpaca-Guanaco Format](./03-alpaca-guanaco-format.md) - Dataset formatting guide
4. [llama.cpp Fine-tuning](./04-llamacpp-finetune.md) - Using llama.cpp for fine-tuning
5. [Unsloth Fine-tuning](./05-unsloth-finetune.md) - Optimized fine-tuning with Unsloth
6. [QLoRA Fine-tuning](./06-qlora-finetune.md) - Memory-efficient fine-tuning
7. [Custom Datasets](./07-custom-datasets.md) - Using CSV/JSON datasets
8. [Code Model Fine-tuning](./08-code-finetune.md) - Fine-tuning for code generation
9. [Reasoning Model Fine-tuning](./09-reasoning-finetune.md) - Fine-tuning for logic/math
10. [Model Evaluation](./10-evaluation.md) - Testing fine-tuned models
11. [Model Export](./11-export-deploy.md) - Exporting and deploying fine-tuned models
12. [Troubleshooting](./12-troubleshooting.md) - Common issues and solutions

## Quick Start

```bash
# Install dependencies
pip install unsloth torch transformers datasets peft accelerate

# Prepare dataset in Alpaca format
python prepare_dataset.py

# Fine-tune with Unsloth
python finetune.py
```

## Available Models for Fine-Tuning

### llama.cpp Models (GGUF)

| Model | Recommended Use | Memory |
|-------|---------------|--------|
| Qwen3 Coder | Code generation | ~16GB |
| Qwen 3.5 27B | General tasks | ~32GB |
| GLM-4.7 Flash | Fast inference | ~16GB |
| Nemotron 120B | High-quality | ~64GB |

### Ollama Models

| Model | Use Case |
|-------|----------|
| mistral | General chat |
| codeqwen | Code tasks |
| mathstral | Math reasoning |
| deepseek-r1:8b | Chain-of-thought |

## Prerequisites

- Jetson AGX Orin 64GB
- JetPack 6.2.2
- Python 3.10+
- CUDA 12.6
- 64GB+ RAM recommended
- 256GB+ NVMe storage

## Next Steps

Start with [Overview](./01-overview.md) to understand fine-tuning concepts, then proceed to [Environment Setup](./02-environment-setup.md) to prepare your system.
