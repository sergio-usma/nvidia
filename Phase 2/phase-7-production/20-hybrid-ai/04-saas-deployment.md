# SaaS Deployment

## Table of Contents

1. [Pricing Models](#pricing-models)
2. [Multi-Tenant Setup](#multi-tenant-setup)
3. [Payment Integration](#payment-integration)
4. [Usage Tracking](#usage-tracking)

## Pricing Models

| Model | Description | Implementation |
|-------|-------------|----------------|
| Free | Limited requests | Rate limiting |
| Pro | Unlimited, priority | API key auth |
| Enterprise | Custom, dedicated | Isolated instances |

## Multi-Tenant Setup

```python
from fastapi import FastAPI, Header
import uuid

app = FastAPI()

# In-memory tenant storage (use database in production)
tenants = {}

@app.post("/tenant/register")
async def register_tenant(name: str):
    tenant_id = str(uuid.uuid4())
    tenants[tenant_id] = {
        "name": name,
        "api_keys": [],
        "usage": 0
    }
    return {"tenant_id": tenant_id}

@app.post("/tenant/{tenant_id}/key")
async def create_api_key(tenant_id: str):
    api_key = f"sk-{uuid.uuid4().hex}"
    tenants[tenant_id]["api_keys"].append(api_key)
    return {"api_key": api_key}

def get_tenant(api_key: str = Header(None)):
    for tid, tenant in tenants.items():
        if api_key in tenant["api_keys"]:
            return tid, tenant
    raise HTTPException(status_code=401)
```

## Payment Integration (Stripe)

```bash
pip install stripe
```

```python
import stripe
from fastapi import FastAPI

stripe.api_key = "sk_test_..."

app = FastAPI()

@app.post("/create-checkout-session")
async def create_checkout_session(price_id: str, tenant_id: str):
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price_id, "quantity": 1}],
        success_url="https://yourdomain.com/success?session_id={CHECKOUT_SESSION_ID}",
        cancel_url="https://yourdomain.com/cancel",
        client_reference_id=tenant_id
    )
    return {"url": session.url}

@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig, "wh_secret"
        )
    except ValueError:
        raise HTTPException(status_code=400)
    
    if event["type"] == "checkout.session.completed":
        # Activate tenant
        tenant_id = event["data"]["object"]["client_reference_id"]
        # Update tenant in database
    
    return {"status": "success"}
```

## Usage Tracking

```python
from datetime import datetime, timedelta

class UsageTracker:
    def __init__(self):
        self.usage = {}
    
    def track(self, tenant_id: str, tokens: int):
        today = datetime.now().date()
        key = f"{tenant_id}:{today}"
        
        if key not in self.usage:
            self.usage[key] = 0
        self.usage[key] += tokens
    
    def get_usage(self, tenant_id: str, days: int = 30):
        total = 0
        for i in range(days):
            date = datetime.now().date() - timedelta(days=i)
            key = f"{tenant_id}:{date}"
            total += self.usage.get(key, 0)
        return total

@app.get("/usage")
async def get_usage(tenant = Depends(get_tenant)):
    tracker = UsageTracker()
    usage = tracker.get_usage(tenant[0])
    return {"tenant": tenant[1]["name"], "usage": usage}
```

## Next Steps

- [Reverse Proxy](./05-reverse-proxy.md) - Nginx + SSL
- [n8n Advanced](./07-n8n-advanced.md) - Automation workflows
