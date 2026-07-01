# Manage GGUF Models

This guide covers model management and provides bash aliases for quick access to your llama.cpp models.

## Model Catalog

| Model Name | Purpose | Launch Command | Delete Command |
|------------|---------|----------------|----------------|
| **Qwen3 Coder** | AI Dev / Coding | `llama-cli -m ~/unsloth/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-UD-Q4_K_XL.gguf -ngl 999 -c 4096` | `rm ~/unsloth/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-UD-Q4_K_XL.gguf` |
| **Qwen 3.5 27B** | General / Logic | `llama-cli -m ~/.cache/llama.cpp/unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf -ngl 999 -c 4096` | `rm ~/.cache/llama.cpp/unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf` |
| **GLM-4.7 Flash** | Speed / Chat | `llama-cli -m ~/unsloth/GLM-4.7-Flash-GGUF/GLM-4.7-Flash-UD-Q4_K_XL.gguf -ngl 999 -c 4096` | `rm ~/unsloth/GLM-4.7-Flash-GGUF/GLM-4.7-Flash-UD-Q4_K_XL.gguf` |
| **Nemotron 120B** | High-End Reasoning | `llama-cli -m ~/Nemotron-Super-GGUF/UD-Q4_K_XL/NVIDIA-Nemotron-3-Super-120B-A12B-UD-Q4_K_XL-00001-of-00003.gguf -ngl 999 -c 2048` | `rm -rf ~/Nemotron-Super-GGUF/` |

## Add Bash Aliases

Add these shortcuts to your `.bashrc` for easy model launching:

```bash
cat << 'EOF' >> ~/.bashrc

# --- LLM Shortcuts for Jetson AGX Orin ---
export PATH="$HOME/llama.cpp:$PATH"

# Function to run llama-cli with optimized Orin settings
run_llm() {
    local model_path=$1
    local context=${2:-4096}
    llama-cli -m "$model_path" \
        --color \
        -ngl 999 \
        -c "$context" \
        -i \
        --temp 0.7 \
        --repeat-penalty 1.1
}

# Specific Aliases
alias run-coder='run_llm ~/unsloth/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-UD-Q4_K_XL.gguf'
alias run-qwen='run_llm ~/.cache/llama.cpp/unsloth_Qwen3.5-27B-GGUF_Qwen3.5-27B-UD-Q4_K_XL.gguf'
alias run-glm='run_llm ~/unsloth/GLM-4.7-Flash-GGUF/GLM-4.7-Flash-UD-Q4_K_XL.gguf'
alias run-nemo='run_llm ~/Nemotron-Super-GGUF/UD-Q4_K_XL/NVIDIA-Nemotron-3-Super-120B-A12B-UD-Q4_K_XL-00001-of-00003.gguf 2048'

EOF

source ~/.bashrc
```

## Using the Aliases

After reloading your bashrc, use these commands:

| Alias | Description |
|-------|-------------|
| `run-coder` | Launch Qwen3 Coder |
| `run-qwen` | Launch Qwen 3.5 27B |
| `run-glm` | Launch GLM-4.7 Flash |
| `run-nemo` | Launch Nemotron 120B |

## Troubleshooting

If you get `llama-cli: command not found`, update the PATH:

```bash
# For build/bin location
export PATH="$HOME/llama.cpp/build/bin:$PATH"
```

## Next Steps

- [Execute models](execute_local_cpp_models.md) directly with full commands
- [Search for more models](search-models-cpp.md) to download
