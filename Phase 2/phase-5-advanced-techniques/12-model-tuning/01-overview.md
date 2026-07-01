# Fine-Tuning Overview

## What is Fine-Tuning?

Fine-tuning is the process of taking a pre-trained Large Language Model (LLM) and training it further on a specific dataset to adapt its behavior for particular tasks or domains.

## Why Fine-Tune on Jetson AGX Orin?

- **Privacy**: Keep all data local
- **Cost**: No API costs after initial setup
- **Customization**: Adapt models to your specific needs
- **Offline**: Works without internet
- **Control**: Full control over the process

## Fine-Tuning Methods

### 1. Full Fine-Tuning
- Updates all model parameters
- Requires significant VRAM (64GB+)
- Highest quality but resource-intensive
- Best for: Large models on powerful hardware

### 2. LoRA (Low-Rank Adaptation)
- Trains small adapter matrices
- ~10-20x less memory than full fine-tuning
- Good quality retention
- Best for: Consumer hardware

### 3. QLoRA (Quantized LoRA)
- Uses 4-bit quantized base model
- Extremely memory efficient
- Runs on 16GB+ GPUs
- Best for: Jetson AGX Orin

### 4. RAG (Retrieval-Augmented Generation)
- Combines fine-tuning with external knowledge
- No model retraining needed
- Best for: Knowledge-intensive tasks

## Understanding Adapter Types

| Type | VRAM Required | Quality | Speed |
|------|---------------|---------|-------|
| Full | 64GB+ | Highest | Slow |
| LoRA | 24GB+ | High | Medium |
| QLoRA | 16GB+ | Good | Fast |

## Choosing a Base Model

### For Code Generation
- **Qwen3 Coder**: Best for general coding
- **codeqwen**: Specialized code tasks
- **mistral**: Balanced performance

### For Reasoning
- **deepseek-r1:8b**: Chain-of-thought
- **mathstral**: Mathematical tasks
- **phi4-mini-reasoning**: Quick decisions

### For General Use
- **mistral-nemo**: Long context
- **GLM-4.7 Flash**: Fast responses
- **Qwen 3.5 27B**: Balanced

## Fine-Tuning Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    Fine-Tuning Pipeline                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Prepare Data ──► 2. Choose Method ──► 3. Train       │
│         │                  │                    │           │
│         ▼                  ▼                    ▼           │
│  Alpaca/Guanaco      LoRA/QLoRA        GPU Training       │
│  Format              vs Full            Run Fine-tune       │
│                                                              │
│         │                  │                    │           │
│         ▼                  ▼                    ▼           │
│                                                              │
│  4. Evaluate ──► 5. Export ──► 6. Deploy                 │
│         │                  │                    │           │
│         ▼                  ▼                    ▼           │
│  Benchmark           GGUF/Ollama        llama.cpp/         │
│  Testing             Format             Ollama Serve       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Expected Outcomes

### Before Fine-Tuning
- Generic responses
- May not understand domain-specific terminology
- Limited task-specific knowledge

### After Fine-Tuning
- Domain-specific responses
- Custom instruction following
- Specialized behavior patterns

## Next Steps

Proceed to [Environment Setup](./02-environment-setup.md) to prepare your Jetson for fine-tuning.
