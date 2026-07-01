# Reverse Proxy

Set up a reverse proxy to securely expose your AI services with SSL/TLS termination.

## Architecture

```
                          Internet
                             │
                             ▼
                    ┌────────────────┐
                    │   Firewall     │
                    │   (Router)     │
                    └───────┬────────┘
                            │
                            ▼
                    ┌────────────────┐
                    │  Nginx Proxy   │
                    │  (Port 80/443) │
                    └───────┬────────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
  ┌────────────┐    ┌────────────┐    ┌────────────┐
  │   Ollama   │    │  Whisper   │    │    API     │
  │  :11434    │    │   :8001    │    │   :5000    │
  └────────────┘    └────────────┘    └────────────┘
```

## Nginx Installation

```bash
sudo apt update
sudo apt install nginx nginx-extras
```

## Basic Configuration

Create `/etc/nginx/sites-available/ai-stack`:

```nginx
upstream ollama_backend {
    server 127.0.0.1:11434;
}

upstream whisper_backend {
    server 127.0.0.1:8001;
}

upstream api_backend {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name ai.yourdomain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name ai.yourdomain.com;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Ollama
    location /ollama/ {
        proxy_pass http://ollama_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # For SSE streaming
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    # Whisper API
    location /whisper/ {
        proxy_pass http://whisper_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        client_max_body_size 100M;
    }

    # API Server
    location /api/ {
        proxy_pass http://api_backend/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        
        client_max_body_size 10M;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "OK\n";
        add_header Content-Type text/plain;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/ai-stack /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## SSL/TLS Setup

### Using Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d ai.yourdomain.com

# Auto-renewal
sudo certbot renew --dry-run
```

### Self-Signed Certificate

```bash
# Generate self-signed certificate
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/key.pem \
    -out /etc/nginx/ssl/cert.pem

# Generate strong DH parameters
sudo openssl dhparam -out /etc/nginx/ssl/dhparam.pem 2048
```

Update SSL configuration:

```nginx
ssl_certificate /etc/nginx/ssl/cert.pem;
ssl_certificate_key /etc/nginx/ssl/key.pem;
ssl_dhparam /etc/nginx/ssl/dhparam.pem;
ssl_protocols TLSv1.2 TLSv1.3;
ssl_prefer_server_ciphers on;
ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
ssl_session_timeout 1d;
ssl_session_cache shared:SSL:50m;
ssl_session_tickets off;

# HSTS
add_header Strict-Transport-Security "max-age=63072000" always;
```

## Rate Limiting

Create `/etc/nginx/nginx.conf` - add in http block:

```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=ollama_limit:10m rate=5r/s;
```

Apply to location:

```nginx
location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    # ... rest of config
}

location /ollama/ {
    limit_req zone=ollama_limit burst=10 nodelay;
    # ... rest of config
}
```

## Caching Configuration

```nginx
# Cache API responses
proxy_cache_path /var/cache/nginx/api levels=1:2 keys_zone=api_cache:10m 
                 max_size=100m inactive=60m use_temp_path=off;

server {
    # ... 
    
    location /api/models {
        proxy_cache api_cache;
        proxy_cache_valid 200 60m;
        proxy_cache_use_stale error timeout http_500 http_502 http_503 http_504;
        add_header X-Cache-Status $upstream_cache_status;
        
        proxy_pass http://api_backend/;
    }
}
```

## WebSocket Support

```nginx
location /ws/ {
    proxy_pass http://api_backend;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_read_timeout 86400;
}
```

## Load Balancing

```nginx
upstream api_backend {
    least_conn;
    
    server 127.0.0.1:5000 weight=5;
    server 127.0.0.1:5001 weight=3;
    server 127.0.0.1:5002 weight=2;
    
    keepalive 32;
}
```

## Monitoring

### Log Analysis

```bash
# View access logs
tail -f /var/log/nginx/access.log

# Analyze with goaccess
sudo apt install goaccess
goaccess /var/log/nginx/access.log --log-format=COMBINED

# Error analysis
tail -f /var/log/nginx/error.log
```

### Status Module

Enable stub status:

```nginx
location /nginx_status {
    stub_status on;
    allow 127.0.0.1;
    allow 192.168.1.0/24;
    deny all;
}
```

## Troubleshooting

### Test Configuration

```bash
# Test nginx config
sudo nginx -t

# Reload after changes
sudo systemctl reload nginx

# Full restart
sudo systemctl restart nginx
```

### Common Issues

**502 Bad Gateway**
```bash
# Check if backend is running
curl http://127.0.0.1:11434/api/tags

# Check nginx error logs
tail -f /var/log/nginx/error.log
```

**SSL Errors**
```bash
# Check certificate
openssl s_client -connect ai.yourdomain.com:443

# Verify certificate dates
openssl x509 -in /etc/nginx/ssl/cert.pem -noout -dates
```

## Next Steps

- [Authentication](./08-authentication.md) - Add authentication layer
- [Backup & Recovery](./09-backup-recovery.md) - Data protection
