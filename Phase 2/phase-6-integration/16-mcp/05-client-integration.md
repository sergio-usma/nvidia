# MCP Client Integration on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Client Setup](#client-setup)
3. [Tool Calling](#tool-calling)
4. [Resource Access](#resource-access)

## Introduction

Connect MCP clients to your Jetson server.

## Client Setup

```python
from mcp import Client

# Connect to Jetson MCP server
client = Client("python mcp_server.py")

# Or via HTTP
# client = Client("http://jetson.local:8000")
```

## Tool Calling

```python
# Call a tool
result = await client.call_tool(
    "run_command",
    {"command": "ls -la"}
)

print(result)
```

## Resource Access

```python
# List resources
resources = await client.list_resources()

# Read resource
data = await client.read_resource("jetson://system")
```

## Next Steps

- [Tools Integration](./06-tools-integration.md)
- [Ollama Integration](./10-ollama-integration.md)
