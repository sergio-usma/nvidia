# Reverse Proxy with Nginx

## Nginx Installation

```bash
sudo apt install nginx

# Enable on boot
sudo systemctl enable nginx
```

## Basic Configuration

```bash
sudo nano /etc/nginx/sites-available/jetson-ai
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    location /ollama/ {
        proxy_pass http://127.0.0.1:11434/;
        proxy_set_header Host $host;
    }

    location /n8n/ {
        proxy_pass http://127.0.0.1:5678/;
        proxy_set_header Host $host;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/jetson-ai /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## SSL with Let's Encrypt

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Advanced: Rate Limiting

```nginx
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    
    server {
        location /api/ {
            limit_req zone=api burst=20 nodelay;
            proxy_pass http://127.0.0.1:5000;
        }
    }
}
```

## Next Steps

- [Webhooks](./06-webhooks.md) - Inbound webhooks
- [n8n Advanced](./07-n8n-advanced.md) - Automation
