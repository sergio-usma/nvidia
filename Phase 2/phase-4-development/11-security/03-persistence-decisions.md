# Persistence Decisions

Control what persists across reboots and make informed choices about your setup.

## What Persists?

| Item | Default | How to Change |
|------|---------|---------------|
| Ollama models | Service: `/usr/share/ollama/` <br> Manual: `~/.ollama/` | Use volume mount |
| Docker containers | Ephemeral | Use volumes |
| Docker images | Persist | Delete manually |
| Python environments | Persist | Delete folder |
| Downloaded models | Persist | Delete folder |
| System settings | Persist | Change config |
| Services | Varies | Use systemctl |

## Ollama Models

By default, models persist in `/usr/share/ollama/.ollama/models`.

To change location:

```bash
# Set environment variable
export OLLAMA_MODELS=/path/to/models
```

Add to `.bashrc` for permanent change.

## Docker Volumes

Always use volumes for persistent data:

```yaml
volumes:
  - ./models:/root/.ollama
```

This ensures models survive container removal.

## Services - Control Autostart

### When to Enable

- Ollama: If you always use LLMs
- Docker: If using containers frequently
- SSH: Always

### When to Disable

- Ollama: If using occasionally (start manually)
- Unused services

## Your Control Options

### Option 1: Always Running (Enabled)

Pros:
- Ready immediately
- No manual start needed

Cons:
- Uses memory always
- May slow boot

### Option 2: Manual Start

Pros:
- Full control
- Saves resources when not in use

Cons:
- Must remember to start

### Option 3: On-Demand (Systemd Socket)

Advanced: Use socket activation to start on first request.

## Making Decisions

Ask yourself:

1. **How often do I use it?**
   - Daily → Enable
   - Weekly → Manual start
   - Monthly → Install when needed

2. **Do I need it immediately?**
   - Yes → Enable
   - No → Manual start

3. **Does it use significant resources?**
   - Yes → Manual start
   - No → Enable

## Example: Ollama Control

```bash
# Disable auto-start
sudo systemctl disable ollama

# Start manually when needed
sudo systemctl start ollama

# Or run in terminal (temporary)
ollama serve
```

## Security Considerations

- Disable unused services
- Use firewall to limit exposure
- Don't expose services to internet without authentication
- Keep system updated

## Summary

| Service | Recommendation |
|---------|---------------|
| Ollama | Manual unless daily use |
| Docker | Enable if using containers |
| SSH | Always enable |
| jtop | Manual when needed |

Your system, your rules. Choose what works best for your use case.

---

## Congratulations!

You now have a fully functional AI development environment on your NVIDIA Jetson AGX Orin. Review the [README](../README.md) for the complete learning path.
