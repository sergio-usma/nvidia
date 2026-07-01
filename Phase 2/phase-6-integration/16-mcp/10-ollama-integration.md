# Ollama MCP Integration on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Setup](#setup)
3. [Configuration](#configuration)
4. [Usage](#usage)

## Introduction

Connect Ollama with MCP for enhanced AI capabilities.

## Setup

```bash
# Install Ollama MCP (if available)
pip install mcp-ollama
```

## Configuration

```json
{
  "mcpServers": {
    "ollama": {
      "command": "python",
      "args": ["-m", "mcp.ollama"]
    }
  }
}
```

## Usage

```python
# Use Ollama with MCP tools
from mcp import Client

# Connect to Ollama
client = Client("ollama://localhost:11434")

# Generate with tool access
result = await client.generate(
    "What is the system status?",
    tools=["system_monitor", "check_gpu"]
)
```

## Next Steps

- [Security](./11-security.md)
- [Troubleshooting](./12-troubleshooting.md)
