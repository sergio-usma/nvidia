# MLC-LLM Setup

MLC-LLM compiles models to machine code for maximum performance. It's more complex but can yield the fastest inference.

## Install Dependencies

```bash
sudo apt install -y cmake build-essential git
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env
```

## Install MLC-LLM Python Package

```bash
pip install mlc-llm
```

## Download Precompiled Model

MLC-LLM provides precompiled models on Hugging Face:

```bash
huggingface-cli download mlc-ai/Llama-3-8B-Instruct-q4f16_1-MLC \
    --local-dir ~/models/Llama-3-8B-Instruct-q4f16_1
```

## Run Chat

```bash
mlc_llm chat ~/models/Llama-3-8B-Instruct-q4f16_1 --device cuda
```

## Serve API

```bash
mlc_llm serve ~/models/Llama-3-8B-Instruct-q4f16_1 --device cuda --port 8000
```

Test:

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Llama-3-8B-Instruct",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Key Parameters

| Parameter | Description |
|-----------|-------------|
| `--device cuda` | Use GPU |
| `--max-gen-len` | Max tokens to generate |
| `--max-input-len` | Max input tokens |
| `--prefill-chunk-size` | Prefill batch size |

## Recommended Models

| Model | Quantization | Size |
|-------|--------------|------|
| Llama-3.1-70B | q4f16_1 | ~43GB |
| Qwen2.5-72B | q4f16_1 | ~47GB |
| DeepSeek-V3 | q3f16_1 | ~35GB |

## Performance Comparison

MLC-LLM often provides the fastest inference because it:
- Compiles models to native code
- Uses TVM for optimization
- Supports advanced quantization

## When to Use MLC-LLM

- Maximum inference speed needed
- Running very large models
- When other methods are too slow

## Next Steps

- [Model Management](04-model-management.md)
- [Swap for Large Models](05-swap-for-large-models.md)
