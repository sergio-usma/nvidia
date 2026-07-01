# Authentication

Implement secure authentication to protect your AI services from unauthorized access.

## Authentication Methods

| Method | Security Level | Use Case |
|--------|---------------|----------|
| API Keys | Medium | Internal APIs |
| Basic Auth | Medium | Simple protection |
| JWT Tokens | High | Stateful apps |
| OAuth 2.0 | Highest | External apps |

## API Key Authentication

### Server-Side Implementation

```python
# api/auth.py
from functools import wraps
from flask import request, jsonify
import hashlib
import hmac
import time

# Store hashed API keys
API_KEYS = {
    "sk-dev-xxxxx": {
        "name": "development",
        "rate_limit": 100,
        "created": "2024-01-01"
    },
    "sk-prod-xxxxx": {
        "name": "production",
        "rate_limit": 1000,
        "created": "2024-01-15"
    }
}

def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()

def require_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'Missing Authorization header'}), 401
        
        try:
            scheme, api_key = auth_header.split()
            if scheme.lower() != 'bearer':
                return jsonify({'error': 'Invalid authentication scheme'}), 401
            
            # Check if key exists
            if api_key not in API_KEYS:
                return jsonify({'error': 'Invalid API key'}), 403
            
            # Add key info to request
            request.api_key_info = API_KEYS[api_key]
            
        except ValueError:
            return jsonify({'error': 'Invalid Authorization header format'}), 401
        
        return f(*args, **kwargs)
    return decorated
```

### Usage in Routes

```python
# api/routes.py
from flask import Blueprint, request, jsonify
from api.auth import require_api_key

api = Blueprint('api', __name__)

@api.route('/v1/chat/completions', methods=['POST'])
@require_api_key
def chat_completion():
    data = request.json
    model = data.get('model', 'qwen2.5-coder')
    messages = data.get('messages', [])
    
    # Process with rate limiting awareness
    rate_limit = request.api_key_info['rate_limit']
    
    # Call Ollama
    response = ollama.chat(model=model, messages=messages)
    
    return jsonify(response)
```

## JWT Token Authentication

### JWT Setup

```bash
# Install PyJWT
pip install PyJWT cryptography
```

### JWT Implementation

```python
# api/jwt_auth.py
import jwt
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify

SECRET_KEY = "your-secure-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_access_token(user_id: str, roles: list) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "roles": roles,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def require_jwt(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return jsonify({'error': 'No token provided'}), 401
        
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != 'bearer':
                return jsonify({'error': 'Invalid scheme'}), 401
            
            payload = decode_token(token)
            if not payload:
                return jsonify({'error': 'Invalid or expired token'}), 401
            
            request.user = payload
            
        except ValueError:
            return jsonify({'error': 'Invalid header'}), 401
        
        return f(*args, **kwargs)
    return decorated

def require_role(role: str):
    def decorator(f):
        @wraps(f)
        @require_jwt
        def decorated(*args, **kwargs):
            if role not in request.user.get('roles', []):
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator
```

### Usage

```python
@api.route('/admin/models', methods=['GET'])
@require_role('admin')
def list_all_models():
    # Admin only
    return jsonify(models)

@api.route('/chat', methods=['POST'])
@require_jwt
def chat():
    # Any authenticated user
    return jsonify({"response": "..."})
```

## OAuth 2.0 Integration

### Flask-Dance Setup

```bash
pip install Flask-Dance flask-oauthlib
```

### OAuth Implementation

```python
# api/oauth.py
from flask import Flask, redirect, url_for
from flask_dance.contrib.google import make_google_blueprint
from flask_dance.contrib.github import make_github_blueprint

app = Flask(__name__)
app.secret_key = "your-secret-key"

# Google OAuth
google_bp = make_google_blueprint(
    client_id="your-google-client-id",
    client_secret="your-google-client-secret",
    scope=["profile", email"]
)
app.register_blueprint(google_bp, url_prefix="/login/google")

# GitHub OAuth
github_bp = make_github_blueprint(
    client_id="your-github-client-id",
    client_secret="your-github-client-secret",
    scope=["user:email"]
)
app.register_blueprint(github_bp, url_prefix="/login/github")

@app.route("/login")
def login():
    return '''
    <a href="/login/google">Login with Google</a><br>
    <a href="/login/github">Login with GitHub</a>
    '''

@app.route("/user")
def user():
    if not google_bp.authorized:
        return redirect(url_for("login"))
    
    resp = google_bp.session.get("/oauth2/v2/userinfo")
    return f"Logged in as: {resp.json()['email']}"
```

## Role-Based Access Control

### RBAC Implementation

```python
# api/rbac.py
from enum import Enum
from functools import wraps
from flask import jsonify

class Role(Enum):
    ADMIN = "admin"
    DEVELOPER = "developer"
    USER = "user"
    VIEWER = "viewer"

PERMISSIONS = {
    Role.ADMIN: ["read", "write", "delete", "manage_users", "manage_models"],
    Role.DEVELOPER: ["read", "write", "manage_models"],
    Role.USER: ["read", "write"],
    Role.VIEWER: ["read"]
}

def check_permission(role: Role, permission: str) -> bool:
    return permission in PERMISSIONS.get(role, [])

def require_permission(permission: str):
    def decorator(f):
        @wraps(f)
        @require_jwt
        def decorated(*args, **kwargs):
            user_role = Role(request.user.get('role', 'viewer'))
            
            if not check_permission(user_role, permission):
                return jsonify({'error': 'Permission denied'}), 403
            
            return f(*args, **kwargs)
        return decorated
    return decorator
```

### Usage

```python
@api.route('/models', methods=['POST'])
@require_permission('manage_models')
def add_model():
    # Only admins and developers
    return jsonify({"status": "model added"})
```

## Nginx Authentication

### Basic Auth

```bash
# Install apache2-utils
sudo apt install apache2-utils

# Create password file
sudo htpasswd -c /etc/nginx/.htpasswd username

# Add additional users
sudo htpasswd /etc/nginx/.htpasswd anotheruser
```

Nginx config:

```nginx
server {
    location /protected {
        auth_basic "Restricted Access";
        auth_basic_user_file /etc/nginx/.htpasswd;
        
        proxy_pass http://localhost:5000;
    }
}
```

## Secure Key Storage

### Environment Variables

```bash
# .env file
OLLAMA_API_KEY=sk-xxxxx
JWT_SECRET_KEY=your-jwt-secret-min-32-chars
OAUTH_CLIENT_SECRET=xxxxx
```

### Python-dotenv

```python
from dotenv import load_dotenv
load_dotenv()

import os
API_KEY = os.getenv("OLLAMA_API_KEY")
```

## Next Steps

- [Backup & Recovery](./09-backup-recovery.md) - Data protection
- [Scaling](./10-scaling.md) - Scale your deployment
