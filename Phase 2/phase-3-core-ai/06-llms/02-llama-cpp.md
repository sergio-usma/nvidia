# llama.cpp Setup

llama.cpp is a lightweight, highly optimized inference engine written in C++. It supports GPU offloading and many quantization formats.

## Install Dependencies

```bash
sudo apt install -y build-essential cmake git
```

## Clone and Build

```bash
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp
mkdir build && cd build
cmake .. -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=87
cmake --build . --config Release -j12
```

The executables (`llama-cli`, `llama-server`) will be in `build/bin/`.

## Add to PATH

```bash
echo 'export PATH=$PATH:~/llama.cpp/build/bin' >> ~/.bashrc
source ~/.bashrc
```

## Download a GGUF Model

Many models are available on Hugging Face in GGUF format:

```bash
pip install huggingface-hub

# Download Qwen2.5-Coder-7B (quantized)
huggingface-cli download bartowski/Qwen2.5-Coder-7B-Instruct-GGUF \
    Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf \
    --local-dir ~/models/qwen2.5-coder-7b
```

## Run Inference

```bash
./llama-cli -m ~/models/qwen2.5-coder-7b/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf \
    -p "Write a Python function to reverse a string." \
    -n 256 \
    --temp 0.7 \
    --ctx-size 4096 \
    --n-gpu-layers 99
```

## Key Parameters

| Parameter | Description |
|-----------|-------------|
| `-m` | Model path |
| `-p` | Prompt |
| `-n` | Number of tokens to generate |
| `--temp` | Creativity (0.0-2.0) |
| `--ctx-size` | Context window size |
| `--n-gpu-layers` | Layers to offload to GPU (99 = all) |
| `--flash-attn` | Use flash attention |

## Serve API

```bash
./llama-server -m ~/models/qwen2.5-coder-7b/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf \
    --host 0.0.0.0 --port 8080 --n-gpu-layers 99
```

This exposes an OpenAI-compatible API at `http://<your-ip>:8080/v1`.

## Example API Call

```bash
curl http://localhost:8080/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Hello",
    "max_tokens": 100
  }'
```

## Persistence

llama.cpp doesn't automatically start any background service. You run it manually each time.

To create a persistent service, see [Systemd Service Setup](../part-10-security/02-service-management.md).

## Recommended Models for 64GB

| Model | Quantization | Size | Layers to GPU |
|-------|--------------|------|---------------|
| Llama-3.1-70B | Q4_K_M | ~43GB | 40-50 |
| Qwen2.5-72B | Q4_K_M | ~47GB | 35-45 |
| DeepSeek-V3 | IQ3_M | ~35GB | 50+ |

## Performance Tips

1. Use `--n-gpu-layers 99` to offload all layers
2. Enable flash attention: `--flash-attn`
3. Use `--ctx-size` appropriate for your RAM
4. Run in MAXN mode: `sudo nvpmodel -m 0`

## Next Steps

- [MLC-LLM](03-mlc-llm.md) - Even higher performance
- [Model Management](04-model-management.md) - Organize your models
