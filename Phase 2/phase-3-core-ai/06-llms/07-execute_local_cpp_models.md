# Execute Local GGUF Models

This guide shows how to run llama.cpp models on your Jetson AGX Orin using the GGUF format.

## Prerequisites

- llama.cpp compiled with CUDA support
- GGUF model files downloaded
- Jetson in MAXN performance mode

## Locate Your Executables

Your llama.cpp binaries are located at:

| Binary | Purpose |
|--------|---------|
| `llama-cli` | Interactive terminal chat |
| `llama-server` | API/Web UI server |

Typical locations:
- `~/llama.cpp/llama-cli`
- `~/llama.cpp/build/bin/llama-cli`

## Available Models

The following GGUF models are ready for inference:

| Model | Path | Notes |
|-------|------|-------|
| **Qwen3 Coder Next** | `~/unsloth/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-UD-Q4_K_XL.gguf` | Excellent for coding tasks |
| **Qwen3.5 27B** | `~/.cache/llama.cpp/unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf` | Balanced for general tasks |
| **GLM-4.7 Flash** | `~/unsloth/GLM-4.7-Flash-GGUF/GLM-4.7-Flash-UD-Q4_K_XL.gguf` | Fast, lightweight queries |
| **Nomic Embed Text v1.5** | `~/.lmstudio/.../nomic-embed-text-v1.5.Q4_K_M.gguf` | Embedding model for RAG |
| **Nemotron-3 Super 120B** | `~/Nemotron-Super-GGUF/UD-Q4_K_XL/...-00001-of-00003.gguf` | Requires ~70GB memory |

## Execute Commands

Use `-ngl 999` to offload all layers to the GPU.

### Qwen3 Coder (Development)

```bash
~/llama.cpp/llama-cli \
  -m ~/unsloth/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-UD-Q4_K_XL.gguf \
  -c 4096 \
  -ngl 999 \
  --color \
  -i \
  -p "You are an expert AI engineer. Please write a Python script that monitors system VRAM and GPU temperature on a Jetson AGX Orin."
```

### Qwen3.5 27B (General Tasks)

```bash
~/llama.cpp/llama-cli \
  -m ~/.cache/llama.cpp/unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf \
  -c 4096 \
  -ngl 999 \
  --color \
  -i \
  -p "You are a maritime English tutor. Generate a vocabulary list for life aboard a merchant vessel."
```

### GLM-4.7 Flash (Fast Chat)

```bash
~/llama.cpp/llama-cli \
  -m ~/unsloth/GLM-4.7-Flash-GGUF/GLM-4.7-Flash-UD-Q4_K_XL.gguf \
  -c 4096 \
  -ngl 999 \
  --color \
  -i
```

### Nemotron 120B (Large Model)

When a model is split across multiple files, point to the first file:

```bash
~/llama.cpp/llama-cli \
  -m ~/Nemotron-Super-GGUF/UD-Q4_K_XL/NVIDIA-Nemotron-3-Super-120B-A12B-UD-Q4_K_XL-00001-of-00003.gguf \
  -c 2048 \
  -ngl 999 \
  --color \
  -i
```

## Key Parameters

| Flag | Description |
|------|-------------|
| `-m` | Path to GGUF model file |
| `-c` | Context window size |
| `-ngl` | Number of GPU layers (999 = all) |
| `-i` | Interactive mode |
| `--color` | Enable colored output |
| `--temp` | Temperature (0.0-1.0) |
| `-n` | Max tokens to generate |

## Running as API Server

Start a local API server:

```bash
~/llama.cpp/llama-server \
  -m ~/unsloth/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-UD-Q4_K_XL.gguf \
  -c 4096 \
  -ngl 999 \
  --port 8080
```

Access at `http://localhost:8080`

## Next Steps

- [Set up bash aliases](remove_local_cpp_models.md) for quick access
- [Find more models](search-models-cpp.md) to download
