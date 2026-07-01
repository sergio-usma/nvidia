# Troubleshooting

## Common Issues

### Connection Refused

```bash
# Check if service is running
ps aux | grep ollama
ps aux | grep nginx

# Check ports
netstat -tlnp | grep 5000
```

### Slow Responses

```bash
# Check CPU/Memory
htop
tegrastats

# Reduce model load
# Use smaller models: mistral, tinyllama
```

### SSL Certificate Issues

```bash
# Renew Let's Encrypt
sudo certbot renew

# Check certificate
sudo certbot certificates
```

### n8n Not Connecting

```bash
# Check n8n logs
docker logs n8n

# Check network
curl http://localhost:5678
```

## Debug Commands

```bash
# Check all services
systemctl status ollama nginx n8n

# Check logs
journalctl -u ollama -f

# Network test
curl -v http://localhost:5000/health
```

## Getting Help

- NVIDIA Jetson Forums
- Ollama GitHub
- n8n Community
