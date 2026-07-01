# Offline Deployment

Run your entire AI stack without internet connectivity for maximum security and reliability.

## Use Cases

- Government and military installations
- Healthcare facilities with patient data
- Financial institutions
- Research labs in remote locations
- Air-gapped development environments

## Preparation

### Download Required Models

Before going offline, download all necessary models:

```bash
# Ollama models
ollama pull qwen2.5-coder
ollama pull llama3.2
ollama pull mistral
ollama pull deepseek-r1
ollama pull nomic-embed-text

# Export model list
ollama list > ~/offline-models.txt
```

### Download Required Dependencies

```bash
# Create offline package directory
mkdir -p ~/offline-packages
cd ~/offline-packages

# Python packages (download wheel files)
pip download -r ~/ai-stack/requirements.txt --platform manylinux_2_17_aarch64 \
    --python-version 3.12 --only-binary=:all: .

# CUDA libraries (copy from host)
rsync -av /usr/local/cuda-12.6/lib64/*.so* ~/offline-packages/cuda/ 2>/dev/null || true
```

### Bundle Everything

```bash
# Create offline bundle
tar -czvf ~/ai-offline-bundle.tar.gz \
    ~/offline-packages/ \
    ~/.ollama/models/ \
    ~/ai-stack/
```

## Offline Installation

### 1. Transfer to Jetson

Use USB drive or secure file transfer:

```bash
# On source machine
cp ~/ai-offline-bundle.tar.gz /media/usb/

# On Jetson (offline)
sudo mount /dev/sda1 /mnt/usb
tar -xzvf /mnt/usb/ai-offline-bundle.tar.gz ~/
```

### 2. Configure Offline Environment

```bash
# Set offline environment variables
export OLLAMA_HOST=0.0.0.0:11434
export OLLAMA_MODELS=~/.ollama/models
export LD_LIBRARY_PATH=~/offline-packages/cuda:$LD_LIBRARY_PATH
export PATH=~/offline-packages/bin:$PATH
```

### 3. Start Services

```bash
# Create offline start script
cat > ~/ai-stack/start-offline.sh << 'EOF'
#!/bin/bash
set -e

# Disable network
sudo systemctl stop NetworkManager
sudo ip link set eth0 down

# Set library paths
export LD_LIBRARY_PATH=~/offline-packages/cuda:$LD_LIBRARY_PATH

# Start Ollama
~/offline-packages/bin/ollama serve &

# Wait for initialization
sleep 5

# Verify offline operation
echo "Testing local inference..."
curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen2.5-coder",
  "prompt": "Hello",
  "stream": false
}'

echo "Offline AI Stack ready"
EOF

chmod +x ~/ai-stack/start-offline.sh
```

## Model Caching Strategy

### Pre-download All Models

```bash
# For each model you'll need
ollama pull qwen2.5-coder:7b
ollama pull qwen2.5-coder:14b
ollama pull codeqwen:7b
ollama pull llama3.2:3b

# Verify models are cached
ollama list
# Output should show all models with size
```

### Model Selection for Offline

| Model | Size | Use Case |
|-------|------|----------|
| qwen2.5-coder:7b | ~4.5GB | Code completion |
| qwen2.5-coder:14b | ~9GB | Complex code |
| llama3.2:3b | ~2GB | General tasks |
| mistral:7b | ~4GB | General tasks |

## Air-Gapped Network Configuration

### Disable Network Services

```bash
# Disable network manager
sudo systemctl mask NetworkManager
sudo systemctl mask systemd-networkd-wait-online

# Block outbound connections
sudo iptables -P OUTPUT DROP
sudo iptables -A OUTPUT -j DROP
```

### Allow Local Only

```bash
# Allow localhost
sudo iptables -A OUTPUT -o lo -j ACCEPT

# Allow specific local services
sudo iptables -A OUTPUT -d 192.168.1.0/24 -j ACCEPT
```

## Verification

### Test Offline Operation

```bash
# Run health check
~/ai-stack/health.sh

# Test model inference
curl -s http://localhost:11434/api/generate -d '{
  "model": "qwen2.5-coder",
  "prompt": "Write a function to calculate fibonacci",
  "stream": false
}' | jq -r '.response'
```

### Resource Usage

Monitor without network tools:

```bash
# Use local monitoring only
tegrastats --interval 1000 &
```

## Offline Updates

### Manual Model Updates

```bash
# On connected machine
ollama pull qwen2.5-coder:latest
docker save ollama/qwen2.5-coder:latest > qwen.tar

# Transfer via physical media
cp qwen.tar /media/usb/

# On offline Jetson
docker load < qwen.tar
```

### Security Considerations

-定期检查安全公告
-使用物理介质传输前扫描病毒
-保持离线系统的物理安全
-记录所有离线更新的审计日志

## 故障排除

### 常见问题

**模型加载失败**
```bash
# 验证模型文件存在
ls -la ~/.ollama/models/blobs/

# 重新注册模型
ollama create custom-model -f Modelfile
```

**CUDA 库缺失**
```bash
# 检查库路径
echo $LD_LIBRARY_PATH

# 手动添加库路径
export LD_LIBRARY_PATH=~/offline-packages/cuda:$LD_LIBRARY_PATH
ldconfig
```

**服务无法启动**
```bash
# 检查日志
journalctl -u ollama -n 50

# 验证端口可用
netstat -tlnp | grep 11434
```

## 后续步骤

- [私有网络](./05-private-network.md) - 安全的内部网络
- [Docker 容器](./06-docker-containers.md) - 容器化部署
