# Network Configuration

## Local Network Setup

### Static IP
```bash
sudo nano /etc/netplan/01-netplan.yaml
```

```yaml
network:
  version: 2
  ethernets:
    eth0:
      addresses:
        - 192.168.1.100/24
      gateway4: 192.168.1.1
      nameservers:
        addresses:
          - 8.8.8.8
```

Apply:
```bash
sudo netplan apply
```

### Firewall
```bash
sudo ufw enable
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 11434/tcp # Ollama
sudo ufw allow 5000/tcp  # API
```

## Dynamic DNS

### For Remote Access
```python
#!/usr/bin/env python3
import requests
import schedule
import time

CF_API_KEY = "your-cloudflare-api-key"
ZONE_ID = "your-zone-id"
RECORD_NAME = "ai.yourdomain.com"

def update_dns():
    ip = requests.get("https://api.ipify.org").text
    
    # Get record ID
    resp = requests.get(
        f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records",
        headers={"Authorization": f"Bearer {CF_API_KEY}"}
    )
    
    records = resp.json()["result"]
    record_id = None
    
    for r in records:
        if r["name"] == RECORD_NAME:
            record_id = r["id"]
            break
    
    # Update
    if record_id:
        requests.put(
            f"https://api.cloudflare.com/client/v4/zones/{ZONE_ID}/dns_records/{record_id}",
            headers={"Authorization": f"Bearer {CF_API_KEY}"},
            json={"type": "A", "name": RECORD_NAME, "content": ip}
        )

schedule.every(10).minutes.do(update_dns)
update_dns()

while True:
    schedule.run_pending()
    time.sleep(60)
```

## Next Steps

- [Local Deployment](./03-local-deployment.md) - Deploy locally
- [Offline Deployment](./04-offline-deployment.md) - Air-gapped setup
