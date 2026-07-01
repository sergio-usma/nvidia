# Best Practices for Jetson

## Performance Optimization

### Enable Max Performance
```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

### Memory Management
```python
import gc
import torch

def cleanup():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
```

### Model Selection
| Task | Recommended Model |
|------|------------------|
| Fast inference | tinyllama, mistrallite |
| Coding | qwen2.5-coder:7b |
| Quality | qwen2.5-coder:14b |

## Deployment

### Service Setup
```bash
# Create systemd service
sudo tee /etc/systemd/system/ai.service << EOF
[Unit]
Description=AI Service
After=network.target

[Service]
Type=simple
User=sergiok
WorkingDirectory=/home/sergiok
ExecStart=/usr/bin/python3 /home/sergiok/main.py
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable ai
sudo systemctl start ai
```

### Resource Limits
```python
import resource
resource.setrlimit(resource.RLIMIT_AS, (8*1024**3, 8*1024**3))  # 8GB
```

## Security

### Environment Variables
```bash
# Never commit secrets
# Use .env files
export API_KEY="your-key"
export OLLAMA_URL="http://localhost:11434"
```

### API Security
```python
# Add rate limiting
# Add API key authentication
# Use HTTPS in production
```

## Checklist

- [ ] Enable max performance mode
- [ ] Set up logging
- [ ] Add health checks
- [ ] Configure memory limits
- [ ] Set up monitoring
- [ ] Use environment variables
- [ ] Add error handling
- [ ] Write tests
- [ ] Document configuration
