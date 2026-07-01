# MCP Protocol Basics on Jetson AGX Orin

## Table of Contents

1. [Protocol Structure](#protocol-structure)
2. [Message Types](#message-types)
3. [Tool Definition](#tool-definition)
4. [Resource Definition](#resource-definition)
5. [Prompt Definition](#prompt-definition)

## Protocol Structure

MCP uses JSON-RPC 2.0 for communication:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {}
}
```

## Message Types

### 1. Initialize

```python
# Client sends
{
  "method": "initialize",
  "params": {
    "protocolVersion": "1.0",
    "capabilities": {}
  }
}

# Server responds
{
  "method": "initialized",
  "params": {
    "protocolVersion": "1.0",
    "capabilities": {
      "tools": {},
      "resources": {},
      "prompts": {}
    }
  }
}
```

### 2. Tools

```python
# List tools
{"method": "tools/list"}

# Call tool
{
  "method": "tools/call",
  "params": {
    "name": "tool_name",
    "arguments": {}
  }
}
```

### 3. Resources

```python
# List resources
{"method": "resources/list"}

# Read resource
{
  "method": "resources/read",
  "params": {
    "uri": "file:///path/to/resource"
  }
}
```

## Tool Definition

```python
from typing import List
from pydantic import BaseModel

class Tool(BaseModel):
    name: str
    description: str
    inputSchema: dict

# Example tool
{
    "name": "run_command",
    "description": "Run a shell command",
    "inputSchema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Command to run"
            }
        },
        "required": ["command"]
    }
}
```

## Resource Definition

```python
class Resource(BaseModel):
    uri: str
    name: str
    description: str
    mimeType: str

# Example resource
{
    "uri": "file:///home/jetson/docs",
    "name": "jetson_docs",
    "description": "Jetson documentation",
    "mimeType": "text/plain"
}
```

## Prompt Definition

```python
class Prompt(BaseModel):
    name: str
    description: str
    arguments: List[dict]

# Example prompt
{
    "name": "analyze_code",
    "description": "Analyze code for issues",
    "arguments": [
        {
            "name": "file_path",
            "description": "Path to code file",
            "required": True
        }
    ]
}
```

## Next Steps

- [Server Implementation](./04-server-implementation.md)
- [Client Integration](./05-client-integration.md)
