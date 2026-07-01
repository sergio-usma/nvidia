# Troubleshooting

Diagnose and resolve common issues with your AI deployment.

## Diagnostic Checklist

```bash
#!/bin/bash
# diagnostics.sh

echo "=== AI Stack Diagnostics ==="
echo ""

echo "1. System Resources"
echo "   Memory: $(free -h | grep Mem | awk '{print $3 "/" $2}')"
echo "   Disk: $(df -h / | tail -1 | awk '{print $3 "/" $2 " (" $5 ")"}')"
echo "   Load: $(uptime | awk -F'load average:' '{print $2}')"
echo ""

echo "2. GPU Status"
tegrastats --interval 1000 --stop
echo ""

echo "3. Service Status"
for svc in ollama nginx; do
    if systemctl is-active --quiet $svc; then
        echo "   $svc: RUNNING"
    else
        echo "   $svc: STOPPED"
    fi
done
echo ""

echo "4. Port Status"
for port in 11434 5000 8001 8002; do
    if netstat -tuln 2>/dev/null | grep -q ":$port "; then
        echo "   Port $port: LISTENING"
    else
        echo "   Port $port: NOT LISTENING"
    fi
done
echo ""

echo "5. Network Connectivity"
curl -sf http://localhost:11434/api/tags > /dev/null 2>&1 && echo "   Ollama: OK" || echo "   Ollama: FAILED"
curl -sf http://localhost:5000/health > /dev/null 2>&1 && echo "   API: OK" || echo "   API: FAILED"
echo ""

echo "6. Recent Errors"
journalctl -n 10 --no-pager -u ollama 2>/dev/null | grep -i error || echo "   No recent errors"
```

## Common Issues

### Ollama Service Issues

**Ollama Won't Start**

```bash
# Check logs
journalctl -u ollama -n 50

# Verify port availability
sudo lsof -i :11434

# Check GPU access
nvidia-smi

# Restart service
sudo systemctl restart ollama

# Verify
curl http://localhost:11434/api/tags
```

**Model Loading Fails**

```bash
# List available models
ollama list

# Check model files
ls -la ~/.ollama/models/

# Remove corrupted model
ollama rm <model_name>

# Re-pull model
ollama pull <model_name>

# Check GPU memory
nvidia-smi
```

### GPU Issues

**GPU Not Available**

```bash
# Check NVIDIA driver
nvidia-smi

# Check CUDA
nvcc --version

# Verify device nodes
ls -la /dev/nvidia*

# Reload NVIDIA kernel modules
sudo modprobe nvidia
sudo modprobe nvidia-uvm
```

**Out of GPU Memory**

```bash
# Check GPU memory usage
nvidia-smi

# Kill占用GPU的进程
nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv

# Use smaller model
# Or reduce GPU layers
OLLAMA_GPU_LAYERS=32 ollama serve
```

### API Server Issues

**500 Internal Server Error**

```bash
# Check API logs
tail -f /var/log/api/error.log

# Test Ollama directly
curl http://localhost:11434/api/tags

# Check environment variables
env | grep -E 'OLLAMA|API|FLASK'

# Restart API service
sudo systemctl restart ai-api
```

**Slow Response Times**

```bash
# Check system load
top
htop

# Check GPU utilization
watch -n 1 nvidia-smi

# Check network
iftop

# Check disk I/O
iostat -x 1 5
```

### Network Issues

**Can't Connect to Services**

```bash
# Check firewall
sudo ufw status

# Check ports
sudo netstat -tulpn | grep -E '11434|5000|8001'

# Test locally
curl http://127.0.0.1:11434/api/tags

# Test from remote
curl http://192.168.1.100:11434/api/tags
```

**SSL Certificate Errors**

```bash
# Check certificate
openssl s_client -connect yourdomain.com:443

# Renew Let's Encrypt
sudo certbot renew

# Check certificate dates
sudo certbot certificates
```

### Docker Issues

**Container Won't Start**

```bash
# Check container logs
docker logs ollama

# Check container status
docker ps -a

# Restart container
docker restart ollama

# Rebuild container
docker compose build
docker compose up -d
```

**GPU Not Available in Container**

```bash
# Check NVIDIA runtime
docker info | grep -i nvidia

# Test GPU access
docker run --rm --gpus all nvidia/cuda:12.6.0-base nvidia-smi

# Check container GPU env
docker exec ollama nvidia-smi
```

## Performance Tuning

### Memory Issues

```bash
# Check system memory
free -h

# Clear cache
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches

# Increase swap
sudo fallocate -l 8G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Thermal Throttling

```bash
# Check temperature
tegrastats

# Improve cooling
# - Clean heatsink/fans
# - Add external cooling
# - Reduce ambient temperature
# - Underclock if needed

# Check for throttling
dmesg | grep -i throttle
```

### Disk Space

```bash
# Find large files
du -sh /* 2>/dev/null | sort -rh | head -10

# Clean Docker
docker system prune -a

# Clean old models
# Remove unused Ollama models
ollama list
ollama rm <unused_model>

# Clean logs
sudo journalctl --vacuum-time=7d
```

## Emergency Recovery

### Service Failure

```bash
# Stop all services
sudo systemctl stop ollama nginx ai-api

# Check for processes
ps aux | grep -E 'ollama|python|nginx'

# Kill remaining processes
sudo pkill -f ollama

# Start services
sudo systemctl start ollama
sleep 5
sudo systemctl start nginx
sudo systemctl start ai-api
```

### Complete System Reset

```bash
# Backup data first
tar -czvf /backup/pre-reset.tar.gz ~/.ollama/models/ ~/ai-stack/

# Stop everything
sudo systemctl stop ollama nginx ai-api
docker compose down

# Clear and restart
rm -rf ~/.ollama/models/
docker system prune -a

# Reboot
sudo reboot
```

## Debugging Tools

### Enable Debug Logging

```bash
# Ollama debug mode
DEBUG=1 ollama serve

# API server debug
export FLASK_DEBUG=1
python -m flask run --host=0.0.0.0 --port=5000

# Nginx debug
sudo nginx -t
sudo systemctl restart nginx
tail -f /var/log/nginx/error.log
```

### Network Debugging

```bash
# Capture HTTP traffic
sudo tcpdump -i eth0 port 11434 -w /tmp/ollama.pcap

# Analyze with Wireshark
wireshark /tmp/ollama.pcap

# Test HTTP headers
curl -v http://localhost:11434/api/tags

# Check DNS
nslookup yourdomain.com
dig yourdomain.com
```

## Get Help

### Collect Debug Info

```bash
#!/bin/bash
# collect-debug-info.sh

echo "Collecting debug information..."

# System info
uname -a > /tmp/debug/system.txt
cat /etc/os-release >> /tmp/debug/system.txt

# GPU info
nvidia-smi > /tmp/debug/gpu.txt 2>&1

# Service status
systemctl status ollama > /tmp/debug/ollama-status.txt 2>&1

# Logs
journalctl -u ollama -n 100 > /tmp/debug/ollama-logs.txt

# Network
netstat -tuln > /tmp/debug/ports.txt

# Create archive
tar -czvf debug-info.tar.gz /tmp/debug/

echo "Debug info saved to debug-info.tar.gz"
```

## Next Steps

Review other parts of the documentation or check related resources.
