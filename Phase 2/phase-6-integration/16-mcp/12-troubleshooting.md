# MCP Troubleshooting on Jetson AGX Orin

## Table of Contents

1. [Introduction](#introduction)
2. [Server Issues](#server-issues)
3. [Client Issues](#client-issues)
4. [Connection Issues](#connection-issues)

## Introduction

Common issues and solutions.

## Server Issues

### Server Not Starting

```
Error: Module not found
```

**Solution:**
```bash
pip install mcp-server
```

### Port Already in Use

```
Error: Address already in use
```

**Solution:**
```bash
# Find and kill process
lsof -i :8000
kill <PID>
```

## Client Issues

### Connection Refused

```
Error: Connection refused
```

**Solution:**
- Check server is running
- Verify port number
- Check firewall settings

### Timeout Errors

```
Error: Request timeout
```

**Solution:**
- Increase timeout
- Check network
- Reduce command complexity

## Connection Issues

### STDIO Not Working

**Solution:**
```bash
# Test with echo
echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | python mcp_server.py
```

This concludes Part 20 - MCP Protocol Integrations.
