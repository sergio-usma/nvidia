# OpenClaw Setup

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Advanced Features](#advanced-features)

## Introduction

OpenClaw is an open-source AI coding assistant focused on CLI operation. It's lightweight and works well with local models on Jetson.

## Installation

### Option 1: Build from Source

```bash
# Install Rust if not present
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env

# Clone repository
git clone https://github.com/smol-ai/openclaw.git
cd openclaw

# Build
cargo build --release

# Install
sudo cp target/release/openclaw /usr/local/bin/
```

### Option 2: Pre-built Binary

```bash
# Check releases for ARM64 builds
wget https://github.com/smol-ai/openclaw/releases/latest/download/openclaw-linux-arm64
chmod +x openclaw-linux-arm64
sudo mv openclaw-linux-arm64 /usr/local/bin/openclaw
```

### Option 3: Using pip

```bash
pip3 install openclaw
```

## Configuration

### Basic Setup

```bash
# Create config directory
mkdir -p ~/.config/openclaw

# Create configuration
cat > ~/.config/openclaw/config.yaml << 'EOF'
# Model provider: ollama, llama.cpp, openai
provider: ollama

# Model name
model: qwen2.5-coder:latest

# API settings
api_base: http://localhost:11434/v1
api_key: not-needed

# Generation settings
temperature: 0.7
max_tokens: 2048
top_p: 0.9
EOF
```

### Ollama Configuration

```yaml
provider: ollama
model: qwen2.5-coder:latest
# Default: http://localhost:11434/v1
# api_base: http://localhost:11434/v1
```

### llama.cpp Configuration

```yaml
provider: llama.cpp
model: /home/user/unsloth/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-UD-Q4_K_XL.gguf
api_base: http://localhost:8080/v1
```

### Environment Variables

```bash
# Alternative: use environment variables
export OPENCLAW_PROVIDER=ollama
export OPENCLAW_MODEL=qwen2.5-coder:latest
export OPENCLAW_API_BASE=http://localhost:11434/v1
```

## Usage

### Interactive Mode

```bash
# Start interactive session
openclaw

# Or with specific model
openclaw --model codeqwen:latest
```

### CLI Commands

```bash
# Single query
openclaw "Write a Python decorator for timing functions"

# Edit file
openclaw --edit main.py "Add type hints to all functions"

# Review code
openclaw --review src/app.py

# Explain code
openclaw --explain bug.py
```

### Options

| Option | Description |
|--------|-------------|
| `--model` | Specify model |
| `--provider` | ollama, llama.cpp, openai |
| `--file` | Edit specific file |
| `--prompt` | Custom prompt |
| `--temperature` | Set temperature |
| `--max-tokens` | Set max tokens |

## Advanced Features

### System Prompts

```yaml
system_prompt: |
  You are an expert Python developer.
  Write clean, well-documented code.
  Follow PEP 8 style guidelines.
```

### Custom Commands

```yaml
commands:
  review:
    prompt: "Review this code for bugs and improvements"
  test:
    prompt: "Write unit tests for this code"
  refactor:
    prompt: "Refactor this code to be more efficient"
```

### Multi-file Analysis

```bash
# Analyze entire project
openclaw --analyze ./src

# Or specific files
openclaw --files file1.py file2.py file3.py
```

### Git Integration

```bash
# Review staged changes
openclaw --git diff --staged

# Explain commit
openclaw --git log -1 --format="%B"

# Write commit message
openclaw --git commit
```

## Integration with Editors

### Neovim Integration

```lua
-- Using nvim-openclaw or custom mapping
vim.api.nvim_set_keymap('n', '<leader>ai', ':!openclaw --file %<CR>', {noremap = true})
```

### Shell Alias

```bash
# Add to ~/.bashrc or ~/.zshrc
alias ai='openclaw'
alias ai-edit='openclaw --edit'
alias ai-review='openclaw --review'
```

## Troubleshooting

### Connection Failed

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Check llama.cpp server
curl http://localhost:8080/v1/models
```

### Model Not Available

```bash
# Pull model
ollama pull qwen2.5-coder:latest

# Or check available models
ollama list
```

### Slow Response

```yaml
# Reduce context in config
max_tokens: 1024
context_size: 2048

# Or use smaller model
model: qwen2.5-coder:7b
```

## Comparison with Other Tools

| Feature | OpenClaw | OpenCode | Aider |
|---------|----------|----------|-------|
| CLI-focused | Yes | Yes | Yes |
| File editing | Yes | Yes | Yes |
| IDE integration | Basic | Good | No |
| Model support | Ollama, llama.cpp | Ollama, llama.cpp | Ollama, llama.cpp, GPT4All |
| ARM64 support | Yes | Yes | Yes |

## Best Practices

1. Use Qwen2.5-Coder for best coding performance
2. Set appropriate context size for your model
3. Use temperature 0.3-0.7 for coding tasks
4. Enable history for conversation continuity

## Next Steps

- [llama.cpp Integration](./07-llama.cpp-integration.md)
- [Ollama Integration](./08-ollama-integration.md)
- [VS Code Integration](./09-vscode-integration.md)
