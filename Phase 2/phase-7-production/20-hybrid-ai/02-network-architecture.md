# Network Architecture

## Table of Contents

1. [Network Configuration](#network-configuration)
2. [Static IP Setup](#static-ip-setup)
3. [Firewall Rules](#firewall-rules)
4. [Dynamic DNS](#dynamic-dns)

## Network Configuration

### Static IP Setup

```bash
# Edit netplan config
sudo nano /etc/netplan/01-netplan.yaml

# Add:
network:
  version: 2
  renderer: networkd
  ethernets:
    eth0:
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
          - 8.8.4.4
```

Apply:
```bash
sudo netplan apply
```

## Firewall Rules

```bash
# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow Ollama
sudo ufw allow 11434/tcp

# Allow n8n
sudo ufw allow 5678/tcp

# Allow custom API
sudo ufw allow 5000/tcp

# Enable firewall
sudo ufw enable
```

## Dynamic DNS

### Using ddclient

```bash
sudo apt install ddclient

# Configure (example for No-IP)
sudo nano /etc/ddclient.conf

# Add:
protocol=dyndns2
use=web
server=dynupdate.no-ip.com
login=your-email
password='your-password'
your-hostname.ddns.net
```

### Cloudflare DDNS

```python
#!/usr/bin/env python3
import requests

# Cloudflare DDNS script
API_KEY = "your-api-key"
ZONE_ID = "your-zone-id"
RECORD = "your-domain.com"
IP = requests.get("https://api.ipify.org").text

requests.put(
    f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records/{RECORD_ID}",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={"type": "A", "name": RECORD, "content": IP}
)
```

## Port Forwarding

Configure your router to forward:
- 80 → 192.168.1.100 (HTTP)
- 443 → 192.168.1.100 (HTTPS)
- 11434 → 192.168.1.100 (Ollama - optional)

## Next Steps

- [API Server](./03-api-server.md) - Build APIs
- [Reverse Proxy](./05-reverse-proxy.md) - Nginx setup
