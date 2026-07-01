# MCP Protocol Overview on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [What is MCP?](#what-is-mcp)
3. [Architecture](#architecture)
4. [Components](#components)
5. [Use Cases](#use-cases)
6. [Jetson Implementation](#jetson-implementation)

## Introduction

The Model Context Protocol (MCP) is an open standard that enables AI models to interact with external tools, services, and data sources in a standardized way. On Jetson AGX Orin, MCP allows you to create powerful AI assistants that can:

- Execute code and commands
- Access file systems
- Query databases
- Call APIs
- Control hardware

## What is MCP?

MCP provides a standardized interface for:

1. **Tools**: Functions the AI can call
2. **Resources**: Data sources the AI can read
3. **Prompts**: Reusable prompt templates
4. **State**: Session and context management

### MCP vs Traditional APIs

| Feature | Traditional API | MCP |
|---------|-----------------|-----|
| Discovery | Manual | Automatic |
| Schema | Custom | Standardized |
| Tool Use | Direct calls | AI-requested |
| Context | Stateless | Stateful |

## Architecture

```
┌─────────────┐     MCP      ┌─────────────┐
│   AI Model  │◄────────────►│ MCP Server  │
└─────────────┘               └─────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    │               │               │
              ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
              │  Tools    │ │ Resources  │ │  Prompts  │
              └───────────┘ └───────────┘ └───────────┘
```

## Components

### 1. MCP Server

The server implements the MCP protocol and exposes:
- Available tools
- Accessible resources
- Prompt templates

### 2. MCP Client

The client (AI model) connects to servers and:
- Discovers capabilities
- Calls tools
- Reads resources
- Uses prompts

### 3. Transport

Communication via:
- STDIO (local)
- HTTP/SSE (remote)
- WebSocket (streaming)

## Use Cases

### 1. Local AI Assistant

```
User → AI → MCP → Execute commands on Jetson
                    → Read files
                    → Run Python code
                    → Control hardware
```

### 2. Knowledge Base

```
AI → MCP → Search documents
             → Query database
             → Access APIs
```

### 3. Automation

```
AI → MCP → Control GPIO
            → Run scripts
            → Monitor sensors
```

## Jetson Implementation

### Running MCP on Jetson

```python
# Simple MCP server on Jetson
from mcp.server import Server
import subprocess

app = Server("jetson-mcp")

@app.list_tools()
async def list_tools():
    return [
        {
            "name": "run_command",
            "description": "Run shell command on Jetson",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "command": {"type": "string"}
                }
            }
        }
    ]

@app.call_tool()
async def call_tool(name, arguments):
    if name == "run_command":
        result = subprocess.run(
            arguments["command"],
            shell=True,
            capture_output=True
        )
        return result.stdout.decode()
```

### Integration with Ollama

See [Ollama Integration](./10-ollama-integration.md) for connecting MCP with local LLMs.

## Next Steps

- [Environment Setup](./02-environment-setup.md) - Install dependencies
- [MCP Basics](./03-mcp-basics.md) - Protocol details
- [Server Implementation](./04-server-implementation.md) - Create MCP server
