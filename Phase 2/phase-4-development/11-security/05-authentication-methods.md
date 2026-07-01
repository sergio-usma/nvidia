# Authentication Methods

This guide covers authentication methods for applications on Jetson AGX Orin.

## JWT Authentication

```python
import jwt
from datetime import datetime, timedelta
import secrets

# Generate secret
secret = secrets.token_hex(32)

def create_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, secret, algorithm='HS256')

def verify_token(token):
    try:
        payload = jwt.decode(token, secret, algorithms=['HS256'])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        return None

# Protected route
@app.route('/protected')
@token_required
def protected():
    return {'message': 'Authorized'}
```

## OAuth 2.0

```python
from authlib.integrations.flask_client import OAuth

oauth = OAuth(app)

google = oauth.register(
    'google',
    client_id='YOUR_CLIENT_ID',
    client_secret='YOUR_CLIENT_SECRET',
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid profile email'}
)

@app.route('/login/google')
def login_google():
    return google.authorize_redirect(redirect_uri=url_for('authorize', _external=True))

@app.route('/authorize')
def authorize():
    token = google.authorize_access_token()
    user = token['userinfo']
    return user
```

## API Keys

```python
import secrets
import hashlib

# Generate API key
api_key = secrets.token_urlsafe(32)

# Hash for storage
key_hash = hashlib.sha256(api_key.encode()).hexdigest()

# Verify
def verify_key(key):
    key_hash = hashlib.sha256(key.encode()).hexdigest()
    return key_hash == stored_hash

# Use in request
@app.route('/api/data')
def get_data():
    api_key = request.headers.get('X-API-Key')
    if not verify_key(api_key):
        return {'error': 'Invalid API key'}, 401
    return {'data': 'value'}
```

## Session Authentication

```python
from flask import Flask, session
from flask.sessions import SecureCookieSessionInterface

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

@app.route('/login', methods=['POST'])
def login():
    session['user_id'] = user.id
    return {'message': 'Logged in'}

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return {'message': 'Logged out'}

@app.route('/profile')
def profile():
    if 'user_id' not in session:
        return {'error': 'Unauthorized'}, 401
    return {'user_id': session['user_id']}
```

## LDAP Authentication

```python
import ldap3

def authenticate_ldap(username, password, server, dn):
    try:
        with ldap3.Connection(server, user=dn, password=password, auto_bind=True) as conn:
            return True
    except ldap3.core.exceptions.LDAPBindError:
        return False

# Usage
if authenticate_ldap('username', 'password', 'ldap://server', 'cn=user,dc=example,dc=com'):
    print("Authenticated")
```

## Password Hashing

```python
import bcrypt

# Hash password
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# Verify password
def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed)

# Usage
hashed = hash_password('password123')
verify_password('password123', hashed)
```

## Two-Factor Authentication

```python
import pyotp

# Generate secret
secret = pyotp.random_base32()

# Generate QR code
totp = pyotp.TOTP(secret)
qr_url = totp.provisioning_uri("user@example.com", issuer_name="MyApp")

# Verify
def verify_2fa(code, secret):
    totp = pyotp.TOTP(secret)
    return totp.verify(code)
```

## SSH Keys

```bash
# Generate key
ssh-keygen -t ed25519 -C "user@jetson"

# Add to authorized_keys
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys

# Connect
ssh -i ~/.ssh/id_ed25519 user@jetson
```

## Token Refresh

```python
from datetime import datetime, timedelta

def create_token_pair(user_id):
    access_token = jwt.encode({
        'user_id': user_id,
        'type': 'access',
        'exp': datetime.utcnow() + timedelta(minutes=15)
    }, secret, algorithm='HS256')
    
    refresh_token = jwt.encode({
        'user_id': user_id,
        'type': 'refresh',
        'exp': datetime.utcnow() + timedelta(days=30)
    }, secret, algorithm='HS256')
    
    return access_token, refresh_token

def refresh_access_token(refresh_token):
    payload = jwt.decode(refresh_token, secret, algorithms=['HS256'])
    if payload['type'] != 'refresh':
        return None
    return create_access_token(payload['user_id'])
```

## Role-Based Access Control

```python
def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = get_token()
            user = get_user(token)
            if user.role not in roles:
                return {'error': 'Forbidden'}, 403
            return f(*args, **kwargs)
        return decorated
    return decorator

@app.route('/admin')
@role_required(['admin'])
def admin():
    return {'message': 'Admin area'}
```
