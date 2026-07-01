# MCP Server Implementation on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Basic Server](#basic-server)
3. [Tool Implementation](#tool-implementation)
4. [Resource Implementation](#resource-implementation)
5. [Server Configuration](#server-configuration)

## Introduction

Create an MCP server on Jetson to expose tools, resources, and prompts to AI models.

## Basic Server

```python
#!/usr/bin/env python3
"""
MCP Server for Jetson AGX Orin
"""

import subprocess
import os
from pathlib import Path
from mcp.server import Server
from mcp.types import Tool, Resource, Prompt
from mcp.server.stdio import stdio_server

class JetsonMCPServer:
    """MCP Server for Jetson"""
    
    def __init__(self):
        self.server = Server("jetson-mcp")
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP handlers"""
        
        @self.server.list_tools()
        async def list_tools():
            """List available tools"""
            return [
                Tool(
                    name="run_command",
                    description="Run a shell command on Jetson",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Command to execute"
                            }
                        },
                        "required": ["command"]
                    }
                ),
                Tool(
                    name="read_file",
                    description="Read a file from Jetson",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "File path to read"
                            }
                        },
                        "required": ["path"]
                    }
                ),
                Tool(
                    name="get_system_info",
                    description="Get Jetson system information",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
            ]
        
        @self.server.call_tool()
        async def call_tool(name, arguments):
            """Handle tool calls"""
            
            if name == "run_command":
                return self._run_command(arguments["command"])
            
            elif name == "read_file":
                return self._read_file(arguments["path"])
            
            elif name == "get_system_info":
                return self._get_system_info()
            
            else:
                return {"error": f"Unknown tool: {name}"}
        
        @self.server.list_resources()
        async def list_resources():
            """List available resources"""
            return [
                Resource(
                    uri="jetson://system",
                    name="system_info",
                    description="Jetson system information",
                    mimeType="application/json"
                ),
                Resource(
                    uri="jetson://gpu",
                    name="gpu_info",
                    description="GPU status and metrics",
                    mimeType="application/json"
                ),
            ]
        
        @self.server.read_resource()
        async def read_resource(uri):
            """Read resource"""
            
            if uri == "jetson://system":
                return self._get_system_info()
            elif uri == "jetson://gpu":
                return self._get_gpu_info()
            
            return {"error": f"Unknown resource: {uri}"}
    
    def _run_command(self, command):
        """Execute shell command"""
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except Exception as e:
            return {"error": str(e)}
    
    def _read_file(self, path):
        """Read file content"""
        
        try:
            with open(path, 'r') as f:
                content = f.read()
            return {"content": content, "path": path}
        except Exception as e:
            return {"error": str(e)}
    
    def _get_system_info(self):
        """Get system information"""
        
        info = {
            "hostname": os.uname().nodename,
            "os": os.uname().sysname,
            "release": os.uname().release,
        }
        
        # CPU info
        try:
            with open('/proc/cpuinfo', 'r') as f:
                info['cpu'] = f.read()[:500]
        except:
            pass
        
        # Memory
        try:
            with open('/proc/meminfo', 'r') as f:
                info['memory'] = f.read()[:500]
        except:
            pass
        
        return info
    
    def _get_gpu_info(self):
        """Get GPU information"""
        
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total,temperature.gpu', '--format=csv,noheader'],
                capture_output=True,
                text=True
            )
            return {"gpu": result.stdout}
        except:
            return {"gpu": "Not available"}
    
    async def run(self):
        """Run the server"""
        async with stdio_server() as streams:
            await self.server.run(
                streams[0],
                streams[1],
                self.server.create_initialization_options()
            )


def main():
    """Main entry point"""
    server = JetsonMCPServer()
    import asyncio
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
```

## Server Configuration

```json
{
  "mcpServers": {
    "jetson": {
      "command": "python",
      "args": ["mcp_server.py"]
    }
  }
}
```

## Next Steps

- [Client Integration](./05-client-integration.md)
- [Jetson Tools](./09-jetson-tools.md)
