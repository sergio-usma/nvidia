# Service Management

Control which services start automatically on your Jetson.

## List Enabled Services

```bash
systemctl list-unit-files --type=service | grep enabled
```

## Common Services

| Service | Description | Auto-start? |
|---------|--------------|--------------|
| ollama | LLM server | Optional |
| docker | Container runtime | Usually |
| ssh | Remote access | Yes |
| jtop | System monitor | No |

## Disable Service

Prevent a service from starting on boot:

```bash
sudo systemctl disable ollama
```

## Enable Service

Allow a service to start on boot:

```bash
sudo systemctl enable ollama
```

## Stop/Start Service

Control service immediately:

```bash
sudo systemctl stop ollama
sudo systemctl start ollama
sudo systemctl restart ollama
```

## Check Service Status

```bash
sudo systemctl status ollama
```

## Create Custom Service

Create `/etc/systemd/system/myapp.service`:

```ini
[Unit]
Description=My AI Application
After=network.target

[Service]
Type=simple
User=nvidia
WorkingDirectory=/home/nvidia
ExecStart=/home/nvidia/start_app.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable myapp
sudo systemctl start myapp
```

## Recommendations

- **Ollama**: Disable if you only use it occasionally
- **Docker**: Keep enabled if using containers
- **jtop**: Only when needed for monitoring

## Next Steps

- [Persistence Decisions](03-persistence-decisions.md)
