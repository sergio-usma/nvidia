# Security Best Practices

This guide covers security best practices for Jetson AGX Orin deployments.

## System Hardening

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable cups

# Configure firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
sudo ufw allow 22/tcp  # SSH
sudo ufw allow 80/tcp  # HTTP
sudo ufw allow 443/tcp # HTTPS
```

## SSH Hardening

```bash
# Edit /etc/ssh/sshd_config
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
MaxAuthTries 3
ClientAliveInterval 300

# Restart SSH
sudo systemctl restart sshd
```

## Fail2Ban

```bash
sudo apt install fail2ban

# Configure
sudo nano /etc/fail2ban/jail.local

[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true

sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

## User Management

```bash
# Create user
sudo adduser username

# Add to sudo group
sudo usermod -aG sudo username

# Set password policy
sudo apt install libpam-pwquality
sudo nano /etc/security/pwquality.conf

# Lock account after failed attempts
sudo nano /etc/pam.d/common-auth
auth required pam_tally2.so deny=5 unlock_time=600
```

## Docker Security

```bash
# Run containers as non-root
docker run --user 1000:1000 myimage

# Limit capabilities
docker run --cap-drop ALL --cap-add NET_BIND_SERVICE myimage

# Read-only root
docker run --read-only myimage

# Resource limits
docker run --memory=512m --cpu-shares=512 myimage
```

## Environment Variables

```bash
# Never commit secrets
echo ".env" >> .gitignore

# Use .env for local
cp .env.example .env

# Production: use secrets manager
```

## Input Validation

```python
from pydantic import BaseModel, validator

class UserInput(BaseModel):
    username: str
    email: str
    age: int
    
    @validator('username')
    def username_alphanumeric(cls, v):
        assert v.isalnum(), 'must be alphanumeric'
        return v
    
    @validator('email')
    def email_valid(cls, v):
        assert '@' in v, 'invalid email'
        return v
    
    @validator('age')
    def age_positive(cls, v):
        assert v > 0, 'must be positive'
        return v
```

## SQL Injection Prevention

```python
# Use parameterized queries
cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))

# Or ORM
user = session.query(User).filter(User.id == user_id).first()
```

## XSS Prevention

```python
# Escape output
from markupsafe import escape

@app.route('/comment', methods=['POST'])
def comment():
    text = request.form['text']
    # Escape before rendering
    safe_text = escape(text)
    return render_template('comment.html', text=safe_text)
```

## CSRF Protection

```python
from flask_wtf import FlaskForm

class MyForm(FlaskForm):
    name = StringField('Name')

@app.route('/form', methods=['GET', 'POST'])
def form():
    form = MyForm()
    if form.validate_on_submit():
        # CSRF token automatically validated
        return 'Success'
    return render_template('form.html', form=form)
```

## Rate Limiting

```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=get_remote_address)

@app.route('/api')
@limiter.limit("100 per minute")
def api():
    return {'data': 'value'}
```

## Security Headers

```python
@app.after_request
def add_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

## Log Security Events

```python
import logging

security_logger = logging.getLogger('security')

def log_login_attempt(username, success):
    security_logger.warning(
        f"Login attempt: user={username}, success={success}, ip={request.remote_addr}"
    )

def log_unauthorized():
    security_logger.warning(
        f"Unauthorized access: path={request.path}, ip={request.remote_addr}"
    )
```

## File Upload Security

```python
import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files['file']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        # Limit file size before saving
        file.save(os.path.join('/uploads', filename))
```

## Audit Checklist

- [ ] System updated
- [ ] Firewall configured
- [ ] SSH hardened
- [ ] Fail2Ban installed
- [ ] Users properly configured
- [ ] Docker running securely
- [ ] Secrets not in code
- [ ] Input validation
- [ ] Rate limiting
- [ ] Security headers
- [ ] Logging enabled
- [ ] Regular backups
