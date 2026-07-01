# Private Network Deployment

Secure your AI services within a private network with controlled access and VPN support.

## Network Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        Private Network                           │
│                                                                  │
│   ┌─────────────┐         ┌─────────────┐                       │
│   │   Router    │─────────│  Jetson     │                       │
│   │  (Firewall) │         │  AGX Orin  │                       │
│   └─────────────┘         └─────────────┘                       │
│        │                        │                                │
│        │                        │                                │
│   ┌─────────────┐         ┌─────────────┐                       │
│   │  Internal   │         │   Client    │                       │
│   │  Clients    │         │  Devices    │                       │
│   └─────────────┘         └─────────────┘                       │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Private Network Setup

### Network Isolation

```bash
# Create isolated network namespace
sudo ip netns add ai-isolated

# Run services in isolated namespace
sudo ip netns exec ai-isolated ollama serve
```

### VLAN Configuration

Configure separate VLAN for AI services:

```bash
# Create VLAN interface
sudo ip link add link eth0 name eth0.100 type vlan id 100

# Assign IP
sudo ip addr add 192.168.100.10/24 dev eth0.100

# Enable
sudo ip link set eth0.100 up
```

## VPN Setup

### WireGuard VPN

Install WireGuard:

```bash
sudo apt install wireguard
```

Generate keys:

```bash
wg genkey | sudo tee /etc/wireguard/private.key
sudo chmod 600 /etc/wireguard/private.key
sudo wg pubkey < /etc/wireguard/private.key | sudo tee /etc/wireguard/public.key
```

Configure `/etc/wireguard/wg0.conf`:

```ini
[Interface]
Address = 10.0.0.1/24
PrivateKey = <SERVER_PRIVATE_KEY>
ListenPort = 51820
PostUp = iptables -A FORWARD -i %i -j ACCEPT
PostUp = iptables -A FORWARD -o %i -j ACCEPT
PostUp = iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE

[Peer]
PublicKey = <CLIENT_PUBLIC_KEY>
AllowedIPs = 10.0.0.2/32
PersistentKeepalive = 25
```

Enable and start:

```bash
sudo systemctl enable wg-quick@wg0
sudo systemctl start wg-quick@wg0
```

### Client Configuration

Client config (`wg-client.conf`):

```ini
[Interface]
Address = 10.0.0.2/24
PrivateKey = <CLIENT_PRIVATE_KEY>
DNS = 1.1.1.1

[Peer]
PublicKey = <SERVER_PUBLIC_KEY>
Endpoint = your-jetson.dyndns.com:51820
AllowedIPs = 10.0.0.0/24
PersistentKeepalive = 25
```

## Firewall Rules

### UFW Configuration

```bash
# Enable firewall
sudo ufw enable

# Default policies
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow VPN
sudo ufw allow 51820/udp

# Allow SSH
sudo ufw allow 22/tcp

# Allow local network
sudo ufw allow from 192.168.1.0/24

# Allow specific services
sudo ufw allow 11434/tcp  # Ollama
sudo ufw allow 5000/tcp   # API

# Verify
sudo ufw status verbose
```

### iptables Rules

```bash
# Allow established connections
sudo iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# Allow loopback
sudo iptables -A INPUT -i lo -j ACCEPT

# Allow SSH
sudo iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# Allow WireGuard
sudo iptables -A INPUT -p udp --dport 51820 -j ACCEPT

# Allow AI services from local network
sudo iptables -A INPUT -s 192.168.1.0/24 -p tcp --dport 11434 -j ACCEPT
sudo iptables -A INPUT -s 192.168.1.0/24 -p tcp --dport 5000 -j ACCEPT

# Drop everything else
sudo iptables -A INPUT -j DROP

# Save rules
sudo iptables-save > /etc/iptables/rules.v4
```

## Access Control

### IP Whitelisting

```python
# api/middleware.py
from functools import wraps
from flask import request, jsonify

ALLOWED_IPS = {
    '192.168.1.100',
    '192.168.1.101',
    '10.0.0.2',  # VPN client
}

def require_ip_whitelist(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        client_ip = request.remote_addr
        if client_ip not in ALLOWED_IPS:
            return jsonify({'error': 'Access denied'}), 403
        return f(*args, **kwargs)
    return decorated
```

### Basic Authentication

```python
# api/auth.py
from flask import request, jsonify
import hashlib
import hmac

API_KEYS = {
    'user1': 'hash_of_secure_password1',
    'user2': 'hash_of_secure_password2',
}

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return jsonify({'error': 'No authorization'}), 401
        
        try:
            scheme, credentials = auth_header.split()
            if scheme.lower() != 'bearer':
                return jsonify({'error': 'Invalid scheme'}), 401
            
            # Verify API key
            if credentials not in API_KEYS.values():
                return jsonify({'error': 'Invalid credentials'}), 403
                
        except ValueError:
            return jsonify({'error': 'Invalid header'}), 401
            
        return f(*args, **kwargs)
    return decorated
```

## Network Monitoring

### Connection Tracking

```bash
# Monitor active connections
sudo conntrack -L

# Monitor specific port
sudo conntrack -L -p tcp --dport 11434
```

### Traffic Analysis

```bash
# Install iftop
sudo apt install iftop

# Monitor bandwidth by connection
sudo iftop -i eth0

# Monitor specific host
sudo iftop -i eth0 -f 'host 192.168.1.100'
```

## Failover Configuration

### Secondary Network Interface

```bash
# Configure secondary interface in /etc/netplan/01-netplan.yaml
network:
  version: 2
  ethernets:
    eth0:
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
    eth1:
      addresses:
        - 192.168.2.100/24
```

### Gateway Failover

```bash
# Install ifmetric
sudo apt install ifmetric

# Set priority (lower = preferred)
sudo ifmetric eth0 100
sudo ifmetric eth1 200
```

## Next Steps

- [Docker Containers](./06-docker-containers.md) - Containerized deployment
- [Reverse Proxy](./07-reverse-proxy.md) - Secure access via proxy
