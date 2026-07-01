# Git and GitHub Setup

Configure Git and connect to GitHub for version control.

## Install Git

```bash
sudo apt install git
```

## Configure Git

```bash
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

## Generate SSH Key

```bash
ssh-keygen -t ed25519 -C "your@email.com"
```

## Add Key to GitHub

1. Copy your public key:

```bash
cat ~/.ssh/id_ed25519.pub
```

2. Go to GitHub > Settings > SSH and GPG keys
3. Add new SSH key
4. Paste your public key

## Test Connection

```bash
ssh -T git@github.com
```

Should see: "Hi <username>! You've successfully authenticated..."

## Common Git Commands

```bash
# Initialize repository
git init

# Clone repository
git clone git@github.com:user/repo.git

# Check status
git status

# Add changes
git add .
git add filename

# Commit
git commit -m "message"

# Push to remote
git push origin main

# Pull from remote
git pull origin main

# Create branch
git checkout -b new-branch

# Switch branch
git checkout main
```

## .gitignore

Create a `.gitignore` file:

```
__pycache__/
*.pyc
.env
data/
models/
*.gguf
*.bin
```

## Next Steps

- [AI Coding Setup](03-ai-coding-setup.md)
- [Monitoring LLM Execution](../part-9-monitoring/02-llm-monitoring.md)
