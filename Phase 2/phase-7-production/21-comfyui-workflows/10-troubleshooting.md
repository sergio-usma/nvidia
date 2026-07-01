# Troubleshooting

## ComfyUI Issues

### Out of Memory

```bash
# Check memory
free -h

# Reduce resolution
# Use 512x512 instead of 1024x1024
```

### Model Not Found

```bash
# Verify models
ls ~/ComfyUI/models/checkpoints/

# Download models
# Place in correct directory
```

### Slow Generation

```bash
# Check GPU usage
tegrastats

# Reduce steps
# Use smaller model
```

## Ollama Issues

### Connection Refused

```bash
# Check Ollama
ps aux | grep ollama

# Restart
ollama serve

# Or start service
sudo systemctl start ollama
```

### Slow Responses

```bash
# Use smaller model
# tinyllama instead of llama3.2:3b
```

## API Issues

### Timeout

```python
# Increase timeout
requests.post(url, json=data, timeout=300)
```

### Port Already in Use

```bash
# Check port
netstat -tlnp | grep 8188

# Kill process
kill -9 <pid>
```

## Debug Commands

```bash
# Check services
systemctl status ollama
systemctl status comfyui

# Check logs
journalctl -u ollama -f
journalctl -u comfyui -f

# Check network
curl http://localhost:11434
curl http://localhost:8188
```

## Getting Help

- ComfyUI GitHub
- Ollama GitHub  
- NVIDIA Jetson Forums
