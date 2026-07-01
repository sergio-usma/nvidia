# OpenCode Setup

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [IDE Integration](#ide-integration)

## Introduction

OpenCode is an open-source AI coding assistant that runs entirely locally. It supports llama.cpp and Ollama backends, making it perfect for Jetson AGX Orin.

## Installation

### Option 1: Official Installer (Recommended)

```bash
# Download and install
curl -sSL https://opencode.ai/install | sh

# Or specify installation directory
curl -sSL https://opencode.ai/install | PREFIX=~/.local sh
```

### Option 2: Build from Source

```bash
# Install dependencies
sudo apt install -y build-essential git

# Clone repository
git clone https://github.com/mryve/opencode.git
cd opencode

# Build
cargo build --release

# Install
sudo cp target/release/opencode /usr/local/bin/
```

### Option 3: Pre-built Binary

```bash
# Download latest release for ARM64
wget https://github.com/mrY-Tek/opencode/releases/latest/download/opencode-linux-arm64
chmod +x opencode-linux-arm64
sudo mv opencode-linux-arm64 /usr/local/bin/opencode
```

## Configuration

### Initial Setup

```bash
# Create config directory
mkdir -p ~/.config/opencode

# Create configuration file
cat > ~/.config/opencode/config.yaml << 'EOF'
provider: ollama
model: qwen2.5-coder:latest

# Alternative: llama.cpp
# provider: llama.cpp
# model: /path/to/model.gguf
EOF
```

### Provider Configuration

#### Ollama Provider

```yaml
provider: ollama
model: qwen2.5-coder:latest
# Optional: specify URL
# base_url: http://localhost:11434
# Optional: context window size
# context_size: 4096
```

#### llama.cpp Provider

```yaml
provider: llama.cpp
model: /home/user/unsloth/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-UD-Q4_K_XL.gguf
context_size: 4096
threads: 12
gpu_layers: 999
```

### Advanced Configuration

```yaml
# Full configuration example
provider: ollama
model: qwen2.5-coder:latest
temperature: 0.7
top_p: 0.9
max_tokens: 2048
context_size: 8192

# System prompt customization
system_prompt: |
  You are an expert AI coding assistant.
  You help write, debug, and refactor code.
  Provide clear explanations with code examples.

# Code-specific settings
code:
  languages:
    - python
    - javascript
    - typescript
    - rust
    - go
  tab_size: 4

# History settings
history:
  enabled: true
  max_entries: 100
```

## Usage

### CLI Mode

```bash
# Interactive mode
opencode

# Single prompt
opencode "Write a Python function to reverse a string"

# Edit file
opencode --file main.py "Add type hints"

# Use specific model
opencode --model qwen3-coder:latest "Explain this code"
```

### Interactive Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/model` | Switch model |
| `/clear` | Clear conversation |
| `/exit` | Exit program |
| `/config` | Show configuration |

### File Editing

```bash
# Edit specific file
opencode --file path/to/file.py

# Edit with instruction
opencode --file main.py --prompt "Add error handling"

# Create new file
opencode --new bot.py --prompt "Create a Discord bot"
```

### Git Integration

```bash
# Review changes
opencode --git diff

# Explain commit
opencode --git commit abc123

# Write commit message
opencode --git commit
```

## IDE Integration

### Neovim

```lua
-- Using nvim-opencode or similar plugin
-- Install plugin
-- Packer
use("yard-smart/opencode.nvim")

-- Configure
require("opencode").setup({
  provider = "ollama",
  model = "qwen2.5-coder:latest"
})

-- Keybindings
vim.keymap.set("n", "<leader>ai", ":Opencode<CR>")
```

### VS Code

Use the **Continue** extension instead:

```bash
# Install Continue extension
# Then configure in settings.json:
```

```json
{
  "continue.extensions": [
    {
      "provider": "openai-compatible",
      "model": "qwen2.5-coder:latest",
      "apiBase": "http://localhost:11434/v1"
    }
  ]
}
```

### Emacs

```elisp
;; Install opencode.el
(add-to-list 'load-path "~/.emacs.d/opencode")
(require 'opencode)

;; Configure
(setq opencode-provider "ollama")
(setq opencode-model "qwen2.5-coder:latest")

;; Keybinding
(global-set-key "\C-cc" 'opencode)
```

## Model Selection

### For Coding Tasks

| Model | Use Case |
|-------|----------|
| `qwen2.5-coder:latest` | General coding (recommended) |
| `codeqwen:latest` | Code generation |
| `qwen3-coder:latest` | Advanced coding |
| `granite3.3:latest` | Enterprise code |

### For General Tasks

| Model | Use Case |
|-------|----------|
| `llama3.2:3b` | General chat |
| `mistral:latest` | Fast general tasks |
| `qwen2.5:14b` | High quality (needs 32GB RAM) |

## Troubleshooting

### Connection Error

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if needed
ollama serve
```

### Model Not Found

```bash
# Pull required model
ollama pull qwen2.5-coder:latest
ollama pull codeqwen:latest
```

### Out of Memory

```yaml
# Reduce context size in config
context_size: 2048
max_tokens: 1024

# Or use smaller model
model: qwen2.5-coder:7b
```

## Next Steps

- [OpenClaw Setup](./06-openclaw-setup.md)
- [VS Code Integration](./09-vscode-integration.md)
- [Model Selection](./10-model-selection.md)
