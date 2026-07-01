# Project 4: AI Coding Assistant with Continue

A comprehensive guide to setting up a complete AI pair programmer using the Continue extension in VS Code with Ollama models for local, private code assistance.

## Table of Contents

1. [Overview](#overview)
2. [Why Continue?](#why-continue)
3. [Architecture](#architecture)
4. [Prerequisites](#prerequisites)
5. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Install Coding Models](#step-1-install-coding-models)
   - [Step 2: Install Continue Extension](#step-2-install-continue-extension)
   - [Step 3: Configure Continue](#step-3-configure-continue)
   - [Step 4: Set Up Embeddings](#step-4-set-up-embeddings)
   - [Step 5: Verify Installation](#step-5-verify-installation)
6. [Using the Coding Assistant](#using-the-coding-assistant)
7. [Advanced Configuration](#advanced-configuration)
8. [Custom Prompts](#custom-prompts)
9. [Troubleshooting](#troubleshooting)
10. [Next Steps](#next-steps)

---

## Overview

This project creates an AI-powered coding environment:

- **Autocompletion**: Code suggestions as you type
- **Code Explanation**: Understand any code segment
- **Refactoring**: Improve code structure
- **Question Answering**: Programming help
- **Codebase Search**: Semantic search across your code

### Why Continue?

| Feature | Benefit |
|---------|---------|
| Local Models | Privacy, no internet needed |
| VS Code Integration | Familiar IDE |
| Multiple Models | Choose right tool for task |
| Custom Prompts | Tailored to your workflow |
| Free & Open Source | No subscription costs |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Coding Assistant Architecture                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐           │
│   │   VS Code    │─────▶│   Continue   │─────▶│   Ollama     │           │
│   │   Editor     │      │   Extension  │      │   Backend    │           │
│   └──────────────┘      └──────────────┘      └──────┬───────┘           │
│                                                       │                    │
│                       ┌───────────────────────────────┼───────────────┐    │
│                       │                               │               │    │
│                       ▼                               ▼               ▼    │
│              ┌──────────────┐              ┌──────────────┐  ┌────────────┐ │
│              │  Qwen2.5    │              │   CodeQwen   │  │ Embeddings│ │
│              │  Coder      │              │   (Chat)     │  │ (Search)  │ │
│              │  (1.5B)     │              │   (7B-14B)   │  │           │ │
│              └──────────────┘              └──────────────┘  └────────────┘ │
│                                                                             │
│   Features:                                                                 │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐    │
│   │  Autocomplete│  │   /edit      │  │   /explain   │  │ Codebase   │    │
│   │  (Tab)       │  │   (Refactor) │  │   (Understand)│  │  Search   │    │
│   └──────────────┘  └──────────────┘  └──────────────┘  └────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Required Software

| Component | Installation Guide |
|-----------|-------------------|
| VS Code | [Part 8: VS Code Setup](../part-8-development-tools/01-vscode-ssh.md) |
| Ollama | [Part 5: Ollama Setup](../part-5-llms/01-ollama-setup.md) |
| Git | [Part 8: GitHub Setup](../part-8-development-tools/02-github-setup.md) |

### Pre-Installation Verification

```bash
# Verify VS Code is installed
code --version

# Verify Ollama
ollama --version

# Verify Git
git --version
```

---

## Step-by-Step Implementation

### Step 1: Install Coding Models

Ollama provides several coding-focused models:

```bash
# Fast model for autocomplete (1.5B parameters - very quick)
# Good for: Real-time autocomplete, less GPU usage
ollama pull qwen2.5-coder:1.5b

# Medium model for chat (7B parameters - balanced)
# Good for: General coding questions, explanations
ollama pull qwen2.5-coder:7b

# Large model for complex tasks (14B parameters - best quality)
# Good for: Complex refactoring, difficult problems
ollama pull qwen2.5-coder:14b

# Alternative: Code-specific models
ollama pull codeqwen

# For codebase embeddings (required for semantic search)
ollama pull nomic-embed-text

# Verify models
ollama list
```

### Model Selection Guide

| Model | Size | Speed | Best For |
|-------|------|-------|----------|
| qwen2.5-coder:1.5b | ~1GB | Very Fast | Autocomplete |
| qwen2.5-coder:7b | ~4GB | Medium | General coding |
| qwen2.5-coder:14b | ~8GB | Slow | Complex tasks |
| codeqwen:7b | ~4GB | Medium | General coding |

### Step 2: Install Continue Extension

1. **Open VS Code**
2. **Go to Extensions** (Ctrl+Shift+X)
3. **Search for "Continue"**
4. **Click Install**

Or install via command line:

```bash
# Install extension from VSIX
code --install-extension continue.continue
```

### Step 3: Configure Continue

Create or edit the Continue configuration file:

```bash
# Create config directory
mkdir -p ~/.continue

# Create config file
cat > ~/.continue/config.json << 'EOF'
{
  "models": [
    {
      "title": "Qwen 14B (Best Quality)",
      "provider": "ollama",
      "model": "qwen2.5-coder:14b",
      "apiBase": "http://localhost:11434"
    },
    {
      "title": "Qwen 7B (Balanced)",
      "provider": "ollama",
      "model": "qwen2.5-coder:7b",
      "apiBase": "http://localhost:11434"
    },
    {
      "title": "CodeQwen",
      "provider": "ollama",
      "model": "codeqwen",
      "apiBase": "http://localhost:11434"
    }
  ],
  "tabAutocompleteModel": {
    "title": "Qwen 1.5B (Fast)",
    "provider": "ollama",
    "model": "qwen2.5-coder:1.5b",
    "apiBase": "http://localhost:11434"
  },
  "embeddingsProvider": {
    "provider": "ollama",
    "model": "nomic-embed-text",
    "apiBase": "http://localhost:11434"
  }
}
EOF
```

### Configuration Options Explained

| Option | Description |
|--------|-------------|
| `models` | List of chat models |
| `tabAutocompleteModel` | Model for autocomplete |
| `embeddingsProvider` | Model for codebase search |

### Step 4: Set Up Embeddings

Continue uses embeddings for semantic code search:

```bash
# Ensure embeddings model is installed
ollama pull nomic-embed-text

# Index your codebase (done automatically by Continue)
# Open a project in VS Code
# Continue will prompt to index
```

### Step 5: Verify Installation

1. **Open VS Code**
2. **Create a new file** (e.g., `test.py`)
3. **Type some code** - you should see autocomplete suggestions
4. **Select code and right-click** - you should see Continue options
5. **Press Ctrl+L** - opens Continue chat sidebar

---

## Using the Coding Assistant

### Autocomplete

Simply start typing code. The model will suggest completions:

```python
# Start typing...
def calculate_fibonacci(n):
    if n <= 1:
        return n
    # Continue will suggest the rest
```

Press **Tab** to accept suggestions.

### Chat Commands

Access the chat panel with **Ctrl+L** or **Cmd+L**:

| Command | Description |
|---------|-------------|
| `/edit` | Edit selected code |
| `/explain` | Explain selected code |
| `/refactor` | Refactor selected code |
| `/test` | Generate tests |
| `/commit` | Generate git commit message |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+L | Open chat |
| Ctrl+Shift+L | Edit selected code |
| Ctrl+Shift+E | Explain selected code |
| Tab | Accept autocomplete |

---

## Advanced Configuration

### Custom System Prompt

Add a custom system prompt in `config.json`:

```json
{
  "models": [
    {
      "title": "Qwen 14B",
      "provider": "ollama",
      "model": "qwen2.5-coder:14b",
      "apiBase": "http://localhost:11434",
      "systemMessage": "You are an expert Python developer. Always provide well-documented, PEP 8 compliant code."
    }
  ]
}
```

### Multiple Model Profiles

Create different configurations for different tasks:

```json
{
  "models": [
    {
      "title": "Python Expert",
      "provider": "ollama", 
      "model": "qwen2.5-coder:14b",
      "systemMessage": "You are a Python expert. Focus on clean, efficient code."
    },
    {
      "title": "Web Dev",
      "provider": "ollama",
      "model": "qwen2.5-coder:7b",
      "systemMessage": "You are a web development expert. Focus on JavaScript, React, and modern CSS."
    }
  ]
}
```

### Model Switching

Switch models in the chat interface:

1. Click the model dropdown in the chat header
2. Select a different model
3. Continue will use the new model for subsequent requests

---

## Custom Prompts

### Creating Custom Commands

Add custom slash commands in `config.json`:

```json
{
  "customCommands": [
    {
      "name": "docstring",
      "prompt": "{{{input}}}\n\nGenerate a detailed docstring for this function following Google style."
    },
    {
      "name": "security",
      "prompt": "{{{input}}}\n\nAnalyze this code for security vulnerabilities and suggest fixes."
    }
  ]
}
```

### Using Custom Commands

```python
# Select code, then type in chat:
/docstring

# Or
/security
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Autocomplete not working | Check `tabAutocompleteModel` in config |
| Model not found | Run `ollama pull <model-name>` |
| Connection refused | Ensure Ollama is running: `ollama serve` |
| Slow responses | Use smaller model for autocomplete |
| Search not working | Ensure embeddings model is installed |

### Debug Mode

Enable debug logging in `config.json`:

```json
{
  "allowAnonymousTelemetry": true,
  "verbose": true
}
```

### Check Ollama Status

```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Check available models
ollama list

# Test model directly
ollama run qwen2.5-coder:7b "Hello, how are you?"
```

---

## Next Steps

| Enhancement | Description |
|-------------|-------------|
| [CodeQwen API Server](08-ai-api-server.md) | REST API for code generation |
| [Multi-Agent System](13-multimodal-agent.md) | Coordinated AI agents |

---

## Related Documentation

- [Continue Documentation](https://docs.continue.dev/)
- [Qwen2.5-Coder Model](https://ollama.com/library/qwen2.5-coder)
- [VS Code Keyboard Shortcuts](https://code.visualstudio.com/docs/getstarted/keybindings)

---

## License

MIT License
