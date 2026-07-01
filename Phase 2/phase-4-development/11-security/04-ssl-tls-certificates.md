# SSL/TLS Certificates

This guide covers SSL/TLS certificate management for Jetson AGX Orin.

## Generate Self-Signed Certificate

```bash
# Generate private key and certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout private.key -out certificate.crt

# With SAN
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout private.key -out certificate.crt \
    -addext "subjectAltName=DNS:example.com,IP:192.168.1.100"
```

## Let's Encrypt

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Generate certificate
sudo certbot --nginx -d example.com -d www.example.com

# Auto-renewal
sudo certbot renew --dry-run

# Add to crontab
sudo crontab -e
# 0 12 * * * /usr/bin/certbot renew --quiet
```

## Nginx SSL Configuration

```nginx
server {
    listen 443 ssl http2;
    server_name example.com;
    
    ssl_certificate /etc/letsencrypt/live/example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/example.com/privkey.pem;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;
    
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    
    location / {
        proxy_pass http://localhost:8000;
    }
}

# HTTP to HTTPS redirect
server {
    listen 80;
    server_name example.com;
    return 301 https://$host$request_uri;
}
```

## Python SSL

```python
import ssl
from flask import Flask

app = Flask(__name__)

context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain('certificate.crt', 'private.key')

if __name__ == '__main__':
    app.run(ssl_context=context, port=443)
```

## Node.js SSL

```javascript
const https = require('https');
const fs = require('fs');

const options = {
  key: fs.readFileSync('private.key'),
  cert: fs.readFileSync('certificate.crt')
};

https.createServer(options, app).listen(443);
```

## Docker SSL

```yaml
services:
  nginx:
    image: nginx
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
```

## Certificate Renewal Script

```bash
#!/bin/bash
# renew.sh

# Stop services
docker-compose stop web

# Renew
certbot renew

# Reload nginx
docker-compose up -d nginx

# Or for plain nginx
systemctl reload nginx
```

## Certificate Monitoring

```python
# Check certificate expiry
from datetime import datetime
import ssl

cert = ssl.get_server_certificate(('example.com', 443))
# Parse and check expiry
```

## ACME Protocol

```python
# Using acme.sh
curl https://get.acme.sh | sh

# Issue certificate
.acme.sh --issue -d example.com --nginx

# Install
.acme.sh --install-cert -d example.com \
  --key-file /path/to/key \
  --fullchain-file /path/to/cert
```

## Certificate Formats

```bash
# PEM to PFX
openssl pkcs12 -export -out certificate.pfx \
    -in certificate.crt -inkey private.key

# PEM to DER
openssl x509 -in certificate.crt -outform der -out certificate.der

# View certificate
openssl x509 -in certificate.crt -text -noout
```

## Client Certificates

```bash
# Generate CA
openssl genrsa -out ca.key 2048
openssl req -new -x509 -days 365 -key ca.key -out ca.crt

# Generate client cert
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr
openssl x509 -req -days 365 -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt
```

## HSTS

```nginx
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

## OCSP Stapling

```nginx
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
```
