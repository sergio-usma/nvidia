# Codex Integration

## Table of Contents

1. [Introduction](#introduction)
2. [Local Alternatives](#local-alternatives)
3. [OpenAI API Compatibility](#openai-api-compatibility)
4. [Setup with Ollama](#setup-with-ollama)
5. [Setup with llama.cpp](#setup-with-llamacpp)
6. [VS Code Integration](#vs-code-integration)

## Introduction

OpenAI Codex is the model behind GitHub Copilot. While Codex itself is not available for local deployment, several excellent alternatives work with VS Code and other editors on Jetson.

## Local Alternatives

### CodeQwen

Best for: General code generation

```bash
# Pull from Ollama
ollama pull codeqwen:latest
```

### Qwen2.5-Coder

Best for: Comprehensive coding tasks

```bash
# Pull from Ollama
ollama pull qwen2.5-coder:latest
ollama pull qwen2.5-coder:14b
```

### Granite-3.3

Best for: Enterprise coding

```bash
# Pull from Ollama
ollama pull granite3.3:latest
```

### DeepSeek-R1

Best for: Reasoning-heavy coding tasks

```bash
# Pull from Ollama
ollama pull deepseek-r1:8b
ollama pull deepseek-r1:14b
```

## OpenAI API Compatibility

Both Ollama and llama.cpp support OpenAI-compatible APIs, enabling integration with many tools.

### Ollama OpenAI Compatibility

Ollama provides OpenAI-compatible endpoints:

| Endpoint | Description |
|----------|-------------|
| `http://localhost:11434/v1/chat/completions` | Chat completions |
| `http://localhost:11434/v1/completions` | Text completions |
| `http://localhost:11434/v1/embeddings` | Embeddings |

### llama.cpp OpenAI Compatibility

Use `server` binary for API:

```bash
# Start API server
./llama-server -m models/qwen2.5-coder.gguf -ngl 999 -c 4096 -port 8080

# Endpoints available:
# http://localhost:8080/v1/chat/completions
# http://localhost:8080/v1/completions
```

## Setup with Ollama

### Basic Configuration

```bash
# Ensure Ollama is running
ollama serve

# Verify API
curl http://localhost:11434/v1/models
```

### Connect Tools

Many tools can connect to Ollama's OpenAI-compatible API:

```python
# Example: Using OpenAI SDK with Ollama
from openai import OpenAI

client = OpenAI(
    api_key="not-needed",
    base_url="http://localhost:11434/v1"
)

response = client.chat.completions.create(
    model="qwen2.5-coder:latest",
    messages=[
        {"role": "user", "content": "Write a hello world in Python"}
    ]
)

print(response.choices[0].message.content)
```

### Configure VS Code Copilot Alternative

1. Install Continue extension (see VS Code guide)
2. Configure `~/.continue/config.py`:

```python
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

## Setup with llama.cpp

### Build llama.cpp

```bash
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
cmake -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j$(nproc)
```

### Start Server

```bash
# Start with your model
./build/bin/llama-server \
    -m ~/unsloth/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-UD-Q4_K_XL.gguf \
    -ngl 999 \
    -c 4096 \
    -port 8080
```

### Connect Tools

```python
from openai import OpenAI

client = OpenAI(
    api_key="not-needed",
    base_url="http://localhost:8080/v1"
)

response = client.chat.completions.create(
    model="qwen3-coder",
    messages=[{"role": "user", "content": "Hello"}]
)
```

## VS Code Integration

### Option 1: Continue.dev

```bash
# Install Continue extension in VS Code
# Then configure:
```

```python
# ~/.continue/config.py
from continuedev.src.continuedev.core.config import ContinueConfig
from continuedev.src.continuedev.models.llms.OpenAI import OpenAI

config = ContinueConfig(
    models=[
        OpenAI(
            model="qwen2.5-coder:latest",
            api_key="not-needed",
            api_base="http://localhost:11434/v1"
        )
    ],
    custom_commands=[
        # Add custom commands
    ]
)
```

### Option 2: CodeGPT (with local provider)

```json
// VS Code settings.json
{
  "codegpt-vscode.extension.apiKey": "not-needed",
  "codegpt-vscode.extension.provider": "custom",
  "codegpt-vscode.extension.custom": {
    "url": "http://localhost:11434/v1/chat/completions"
  }
}
```

### Option 3: Using copilot.lua (emulation)

```lua
-- copilot.lua configuration for local model
require("copilot").setup({
  suggestion = {
    enabled = true,
    auto_trigger = true,
  },
  filetypes = {
    python = true,
    javascript = true,
    typescript = true,
  }
})
```

## Model Selection by Language

| Language | Recommended Model |
|----------|-----------------|
| Python | qwen2.5-coder, codeqwen |
| JavaScript/TypeScript | qwen2.5-coder, qwen3-coder |
| C/C++ | granite3.3, deepseek-r1 |
| Rust | qwen3-coder, llama3.2 |
| Go | codeqwen, qwen2.5-coder |
| Java | granite3.3 |
| General | mistral-nemo, qwen2.5-coder |

## Performance Notes

For best performance on Jetson:

```bash
# Use smaller models for speed
ollama pull qwen2.5-coder:7b
# or
ollama pull codeqwen:7b

# For better quality, use larger models
ollama pull qwen2.5-coder:14b
# Note: 14b requires more VRAM
```

## Next Steps

- [OpenCode Setup](./05-opencode-setup.md)
- [VS Code Integration](./09-vscode-integration.md)
- [Model Selection](./10-model-selection.md)
