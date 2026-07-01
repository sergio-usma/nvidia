# Claude Code Setup

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Usage](#usage)
5. [Integration with Local Models](#integration-with-local-models)

## Introduction

Claude Code is Anthropic's CLI tool for AI-assisted coding. While the core requires API access, it can be configured to work with local inference servers through compatible endpoints.

## Installation

### Option 1: npm (Recommended)

```bash
# Install Node.js first if not present
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version
```

### Option 2: Binary Release

```bash
# Download the latest release for ARM64
wget https://github.com/anthropics/claude-code/releases/latest/download/claude-linux-arm64

# Make executable
chmod +x claude-linux-arm64

# Install to PATH
sudo mv claude-linux-arm64 /usr/local/bin/claude

# Verify
claude --version
```

## Configuration

### API Key Setup

```bash
# Set Anthropic API key
export ANTHROPIC_API_KEY="sk-ant-your-api-key-here"

# Or use config file
mkdir -p ~/.claude
echo 'ANTHROPIC_API_KEY="sk-ant-your-api-key"' > ~/.claude/config.env
```

### Proxy Configuration (for local models)

To use Claude Code with local models, you need an API-compatible proxy:

```bash
# Install liteLLM for API translation
pip3 install litellm

# Create proxy configuration
cat > ~/.claude/proxy.yaml << 'EOF'
model_list:
  - model_name: local-qwen
    litellm_params:
      model: openai/qwen2.5-coder
      api_base: http://localhost:11434/v1
      api_key: dummy-key

  - model_name: local-llama
    litellm_params:
      model: openai/llama3.2:3b
      api_base: http://localhost:11434/v1
      api_key: dummy-key
EOF
```

### Environment Variables

```bash
# Ollama-compatible API
export ANTHROPIC_API_BASE="http://localhost:11434/v1"

# Or use LiteLLM proxy
export ANTHROPIC_API_BASE="http://localhost:4000/v1"
```

## Usage

### Basic Commands

```bash
# Start interactive session
claude

# Run with specific prompt
claude "Write a Python function to calculate fibonacci"

# Analyze code
claude --file main.py

# Use with git
claude "review the changes in this commit"
```

### Claude Code Commands

Within the interactive session:

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/review` | Review current code |
| `/test` | Generate tests |
| `/refactor` | Refactor code |
| `/commit` | Create git commit |
| `Ctrl+C` | Exit session |

## Integration with Local Models

### Method 1: Ollama with OpenAI Compatibility

```bash
# Ensure Ollama has OpenAI-compatible endpoint
# Ollama v0.1.20+ supports /v1/chat/completions

# Configure Claude Code to use local endpoint
export ANTHROPIC_API_KEY="not-needed"
export ANTHROPIC_API_BASE="http://localhost:11434/v1"

# Note: Claude Code requires Anthropic format, so use proxy
```

### Method 2: LiteLLM Proxy (Recommended)

```bash
# Start LiteLLM proxy
litellm --config ~/.claude/proxy.yaml --port 4000

# Configure Claude Code
export ANTHROPIC_API_BASE="http://localhost:4000/v1"
export ANTHROPIC_API_KEY="sk-dummy"
```

### Method 3: Alternative Local Tools

Since Claude Code's local support is limited, consider:

| Tool | Local Support | Recommendation |
|------|---------------|----------------|
| OpenCode | Full | Use instead |
| Aider | Full | Use for CLI editing |
| Continue.dev | Full | Use with VS Code |

## Troubleshooting

### API Connection Failed

```bash
# Check if local server is running
curl http://localhost:11434/api/tags

# Check port is accessible
netstat -tlnp | grep 11434
```

### Model Not Found

```bash
# Pull required model
ollama pull qwen2.5-coder:latest
```

### Authentication Error

```bash
# Check API key is set
echo $ANTHROPIC_API_KEY

# For local models, use dummy key
export ANTHROPIC_API_KEY="not-needed"
```

## Alternative: Use OpenCode Instead

For fully local operation without API:

```bash
# Install OpenCode (see dedicated guide)
curl -sSL https://opencode.ai/install | sh

# Configure with local Ollama
opencode config set provider ollama
opencode config set model qwen2.5-coder:latest
```

## Next Steps

- [OpenCode Setup](./05-opencode-setup.md)
- [OpenClaw Setup](./06-openclaw-setup.md)
- [Model Selection](./10-model-selection.md)
