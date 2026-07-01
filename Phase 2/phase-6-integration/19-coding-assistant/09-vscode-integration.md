# VS Code Integration

## Table of Contents

1. [Introduction](#introduction)
2. [Remote Development Setup](#remote-development-setup)
3. [Continue Extension](#continue-extension)
4. [CodeGPT Setup](#codegpt-setup)
5. [Other Extensions](#other-extensions)
6. [Keybindings](#keybindings)

## Introduction

Integrate AI coding tools with VS Code for a powerful local development environment on Jetson.

## Remote Development Setup

### SSH into Jetson

1. Install VS Code on your local machine
2. Install "Remote - SSH" extension
3. Connect to Jetson:

```bash
# From VS Code:
# Ctrl+Shift+P → Remote-SSH: Connect to Host
# Enter: sergiok@jetson-ip
```

### Configure SSH Key

```bash
# Generate SSH key (on local machine)
ssh-keygen -t ed25519

# Copy to Jetson
ssh-copy-id sergiok@jetson-ip
```

### Recommended Extensions (Remote)

Install on Jetson via SSH:

- Python
- Jupyter
- GitLens
- Docker
- YAML
- JSON

## Continue Extension

### Installation

1. Install "Continue" extension in VS Code
2. Connect to your Jetson via SSH

### Configuration

Create `~/.continue/config.py`:

```python
from continuedev.src.continuedev.core.config import ContinueConfig
from continuedev.src.continuedev.models.llms import OpenAI

config = ContinueConfig(
    models=[
        OpenAI(
            model="qwen2.5-coder:latest",
            api_key="not-needed",
            api_base="http://localhost:11434/v1"
        )
    ]
)
```

### Alternative: Ollama Configuration

```python
from continuedev.src.continuedev.models.llms import Ollama

config = ContinueConfig(
    models=[
        Ollama(
            model="qwen2.5-coder:latest"
        )
    ]
)
```

### Alternative: llama.cpp

```python
from continuedev.src.continuedev.models.llms import OpenAI

config = ContinueConfig(
    models=[
        OpenAI(
            model="qwen3-coder",
            api_key="not-needed",
            api_base="http://localhost:8080/v1"
        )
    ]
)
```

### Using Continue

| Action | How |
|--------|-----|
| Chat | Ctrl+Shift+P → Continue: Chat |
| Edit | Select code → Ctrl+Shift+L |
| Generate | Ctrl+I |
| Complete | Tab |

## CodeGPT Setup

### Installation

1. Install "CodeGPT" extension in VS Code
2. Restart VS Code

### Configuration

```json
// settings.json
{
  "codegpt-vscode.extension.apiKey": "not-needed",
  "codegpt-vscode.extension.provider": "custom",
  "codegpt-vscode.extension.custom": {
    "url": "http://localhost:11434/v1/chat/completions"
  },
  "codegpt-vscode.extension.model": "qwen2.5-coder:latest"
}
```

### Alternative: Ollama Provider

```json
{
  "codegpt-vscode.extension.provider": "ollama",
  "codegpt-vscode.extension.apiBase": "http://localhost:11434"
}
```

## Other Extensions

### CodeWhisperer Alternative (Lambda)

1. Install "AWS Toolkit" extension
2. Configure with local endpoint (limited support)

### Tabby AI

```bash
# Install Tabby ML server
pip3 install tabby

# Run locally
tabby serve --model Qwen2.5-Coder

# VS Code: Install Tabby extension
# Configure: http://localhost:8080
```

### Codeium

```json
// settings.json - Note: Requires cloud for full features
{
  "codeium.enable": true,
  "codeium.portalUrl": "http://localhost:8080"
}
```

### AI Assistant (Generic)

```json
// Using HTTP Request extension
{
  "ai-assistant.model": "qwen2.5-coder:latest",
  "ai-assistant.apiUrl": "http://localhost:11434/v1/chat/completions",
  "ai-assistant.apiKey": "not-needed"
}
```

## Keybindings

### Recommended Bindings

```json
// keybindings.json
[
  {
    "key": "ctrl+shift+l",
    "command": "continue.chatSelected",
    "when": "editorTextFocus"
  },
  {
    "key": "ctrl+i",
    "command": "continue.inlineEdit",
    "when": "editorTextFocus"
  },
  {
    "key": "ctrl+shift+space",
    "command": "editor.action.triggerSuggest",
    "when": "editorHasCompletionItemProvider"
  }
]
```

## Using SSH Config

```bash
# ~/.ssh/config
Host jetson
    HostName 192.168.1.xxx
    User sergiok
    ForwardAgent yes
    ServerAliveInterval 60
```

## Performance Optimization

### Reduce Latency

```json
// settings.json
{
  "remote.SSH.showLoginTerminal": false,
  "remote.SSH.configFile": "~/.ssh/config"
}
```

### Disable Unnecessary Extensions

Only install extensions you need on the remote:

```bash
# List installed extensions (on Jetson)
code --list-extensions

# Install specific extension
code --install-extension ms-python.python
```

## Troubleshooting

### Connection Issues

```bash
# Test SSH connection
ssh -v sergiok@jetson-ip

# Check port
ssh -p 22 sergiok@jetson-ip
```

### Extension Not Working

```bash
# Reload window
Ctrl+Shift+P → Developer: Reload Window

# Check logs
View → Output → Extension Host
```

### Model Not Responding

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Test API
curl http://localhost:11434/v1/models
```

## Complete Setup Example

1. **SSH to Jetson**: `ssh jetson`

2. **Start Ollama**: `ollama serve &`

3. **Pull model**: `ollama pull qwen2.5-coder:latest`

4. **Open VS Code locally**: Connect via SSH

5. **Install Continue**: Search in Extensions

6. **Configure**: Add config to `~/.continue/config.py`

7. **Start coding**: Use AI assistance!

## Next Steps

- [Model Selection](./10-model-selection.md)
- [Custom Prompts](./11-custom-prompts.md)
- [Performance](./12-performance.md)
