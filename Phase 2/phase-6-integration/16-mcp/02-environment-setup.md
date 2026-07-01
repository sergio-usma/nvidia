# MCP Environment Setup on Jetson AGX Orin

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Python Dependencies](#python-dependencies)
3. [MCP Installation](#mcp-installation)
4. [Verification](#verification)

## System Requirements

- Jetson AGX Orin 64GB
- JetPack 6.2.2
- Python 3.10+
- Ollama (from Part 9-12)

## Python Dependencies

```bash
# Install MCP
pip install mcp-server

# Install additional dependencies
pip install pydantic httpx sse-starlette
```

## MCP Installation

```bash
# Create project directory
mkdir -p ~/mcp-project
cd ~/mcp-project

# Initialize
pip install -e .
```

## Verification

```python
# Test MCP import
python -c "from mcp.server import Server; print('✅ MCP OK')"
```

## Next Steps

- [MCP Basics](./03-mcp-basics.md) - Protocol details
- [Server Implementation](./04-server-implementation.md)
