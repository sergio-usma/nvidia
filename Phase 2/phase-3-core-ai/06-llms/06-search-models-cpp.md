# Search and Find GGUF Models

This guide helps you locate GGUF model files and llama.cpp binaries on your Jetson AGX Orin.

## Find GGUF Model Files

Search for GGUF files in your home directory:

```bash
find ~ -type f -name "*.gguf" 2>/dev/null
```

Search the entire filesystem:

```bash
sudo find / -type f -name "*.gguf" 2>/dev/null
```

## Find llama.cpp Binaries

Find the compiled executables:

```bash
find ~ -type f \( -name "llama-cli" -o -name "main" -o -name "llama-server" \) 2>/dev/null
```

Common locations:
- `~/llama.cpp/llama-cli`
- `~/llama.cpp/build/bin/llama-cli`

## Run Models with Full GPU Acceleration

The Jetson AGX Orin uses unified memory. Use `-ngl 999` to offload all layers to the GPU.

### Interactive Chat Mode

```bash
./llama-cli -m /path/to/model.gguf \
  -c 4096 \
  -ngl 999 \
  --color \
  -i \
  -p "You are a helpful AI assistant."
```

### API Server Mode

```bash
./llama-server -m /path/to/model.gguf \
  -c 4096 \
  -ngl 999 \
  --port 8080
```

## Parameter Reference

| Flag | Description |
|------|-------------|
| `-m` | Path to GGUF model file |
| `-c` | Context window size |
| `-ngl` | GPU layers (999 = all) |
| `-i` | Interactive mode |
| `-p` | Prompt to start with |
| `--port` | Server port (llama-server) |

## Download Models from Hugging Face

Install huggingface-cli:

```bash
pip install -U "huggingface_hub[cli]"
```

Set your token:

```bash
export HUGGINGFACE_TOKEN="hf_..."
huggingface-cli login --token $HUGGINGFACE_TOKEN
```

Download a model:

```bash
huggingface-cli download unsloth/llama-3-8b-Instruct-GGUF \
  llama-3-8b-Instruct-Q4_K_M.gguf \
  --local-dir ~/models/
```

## Next Steps

- [Execute models](execute_local_cpp_models.md) with full commands
- [Manage models](remove_local_cpp_models.md) with aliases
