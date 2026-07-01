# Firewall Setup

Secure your Jetson with UFW (Uncomplicated Firewall).

## Install UFW

```bash
sudo apt install ufw
```

## Basic Configuration

### Allow SSH (Important!)

```bash
sudo ufw allow ssh
```

Or specifically:

```bash
sudo ufw allow 22/tcp
```

### Allow Ollama

```bash
sudo ufw allow 11434/tcp
```

### Allow llama.cpp Server

```bash
sudo ufw allow 8080/tcp
```

### Allow MLC-LLM

```bash
sudo ufw allow 8000/tcp
```

### Allow WebUI

```bash
sudo ufw allow 3000/tcp
```

## Enable Firewall

```bash
sudo ufw enable
```

## Check Status

```bash
sudo ufw status verbose
```

## Common Commands

| Command | Description |
|---------|-------------|
| `sudo ufw status` | Show status |
| `sudo ufw allow <port>` | Allow port |
| `sudo ufw deny <port>` | Block port |
| `sudo ufw remove allow <port>` | Remove rule |
| `sudo ufw disable` | Disable firewall |

## Example: Only SSH and Ollama

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 11434/tcp
sudo ufw enable
```

## Next Steps

- [Service Management](02-service-management.md)
- [Persistence Decisions](03-persistence-decisions.md)
