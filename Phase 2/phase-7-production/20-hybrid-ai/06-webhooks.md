# Webhooks

## Table of Contents

1. [Inbound Webhooks](#inbound-webhooks)
2. [Outbound Webhooks](#outbound-webhooks)
3. [Webhook Security](#webhook-security)

## Inbound Webhooks

### Flask Server

```python
from flask import Flask, request, jsonify
import hmac
import hashlib

app = Flask(__name__)
SECRET = "your-webhook-secret"

def verify_signature(payload, signature):
    expected = hmac.new(
        SECRET.encode(), 
        payload, 
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Webhook-Signature")
    
    if not verify_signature(request.data, signature):
        return jsonify({"error": "Invalid signature"}), 401
    
    data = request.json
    
    # Process webhook
    action = data.get("action")
    
    if action == "chat":
        # Process chat request
        response = process_chat(data["message"])
        return jsonify({"response": response})
    
    return jsonify({"status": "ok"})

def process_chat(message):
    # Call local AI
    import requests
    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "qwen2.5-coder:latest", "prompt": message}
    )
    return resp.json()["response"]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

## Outbound Webhooks

```python
import requests
import hmac
import hashlib

def send_webhook(url, payload, secret):
    import json
    body = json.dumps(payload)
    signature = hmac.new(
        secret.encode(), 
        body.encode(), 
        hashlib.sha256
    ).hexdigest()
    
    response = requests.post(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature
        }
    )
    return response

# Usage
send_webhook(
    "https://your-domain.com/webhook",
    {"event": "completion", "result": "..."},
    "recipient-secret"
)
```

## Webhook Security

```python
# Rate limiting
from functools import wraps
import time

rate_limit = {}

def rate_limited(max_calls=10, period=60):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            now = time.time()
            key = request.remote_addr
            
            if key not in rate_limit:
                rate_limit[key] = []
            
            rate_limit[key] = [
                t for t in rate_limit[key] 
                if now - t < period
            ]
            
            if len(rate_limit[key]) >= max_calls:
                return jsonify({"error": "Rate limit exceeded"}), 429
            
            rate_limit[key].append(now)
            return f(*args, **kwargs)
        return wrapper
    return decorator
```

## Next Steps

- [n8n Advanced](./07-n8n-advanced.md) - Automation workflows
- [External Services](./08-external-services.md) - Connect to APIs
