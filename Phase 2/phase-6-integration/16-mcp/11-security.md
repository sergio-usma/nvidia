# MCP Security on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Security Best Practices](#security-best-practices)
3. [Command Restrictions](#command-restrictions)
4. [Access Control](#access-control)

## Introduction

Secure your MCP server on Jetson.

## Security Best Practices

### 1. Command Whitelisting

```python
# Only allow specific commands
ALLOWED_COMMANDS = [
    "ls",
    "cat",
    "git",
    "python",
]

def _run_command(self, command):
    # Check if command is allowed
    cmd = command.split()[0]
    if cmd not in ALLOWED_COMMANDS:
        return {"error": "Command not allowed"}
```

### 2. Path Restrictions

```python
ALLOWED_PATHS = [
    "/home/jetson",
    "/workspace",
]

def _read_file(self, path):
    # Check path
    for allowed in ALLOWED_PATHS:
        if path.startswith(allowed):
            return self._read_file_impl(path)
    
    return {"error": "Path not allowed"}
```

## Command Restrictions

```python
# Block dangerous commands
BLOCKED_PATTERNS = [
    "rm -rf",
    "dd if=",
    "mkfs",
    ":(){:|:&};:",  # Fork bomb
]

def _is_safe(self, command):
    for pattern in BLOCKED_PATTERNS:
        if pattern in command:
            return False
    return True
```

## Access Control

```python
# Add authentication
async def authenticate(self, token):
    valid_tokens = ["your-secure-token"]
    return token in valid_tokens
```

## Next Steps

- [Troubleshooting](./12-troubleshooting.md)
