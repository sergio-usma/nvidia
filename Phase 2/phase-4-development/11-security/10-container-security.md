# Container Security

This guide covers container security best practices for Jetson AGX Orin.

## Security Principles

1. **Least Privilege**: Run containers with minimal permissions
2. **Image Scanning**: Check for vulnerabilities
3. **Read-Only Filesystem**: Prevent modifications
4. **Network Isolation**: Separate container networks
5. **Secret Management**: Don't hardcode secrets

## Non-root Users

```dockerfile
FROM node:18-alpine

RUN addgroup -g 1001 appgroup && \
    adduser -u 1001 -G appgroup -s /bin/sh -D appuser

USER appuser
```

## Read-Only Container

```bash
docker run --read-only myapp

# With tmpfs for write needs
docker run --read-only --tmpfs /tmp myapp
```

## Capability Dropping

```bash
# Drop all, add only needed
docker run --cap-drop ALL --cap-add NET_BIND_SERVICE myapp
```

## Security Profiles

```bash
# seccomp profile
docker run --security-opt seccomp=default myapp

# AppArmor profile
docker run --security-opt apparmor=default myapp

# No new privileges
docker run --security-opt no-new-privileges:true myapp
```

## Image Scanning

```bash
# Trivy
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy image myimage:latest

# Dockle
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    goodwithgod/dockle myimage:latest
```

## Docker Bench

```bash
docker run --rm -it \
    --privileged \
    -v /var/run/docker.sock:/var/run/docker.sock \
    docker/docker-bench-security
```

## Secret Management

```bash
# Docker secrets
echo "mypassword" | docker secret create db_password -

# Use in compose
docker stack deploy -c docker-compose.yml myapp
```

## Network Isolation

```yaml
# docker-compose.yml
services:
  app:
    networks:
      - internal
  
  db:
    networks:
      - internal

networks:
  internal:
    driver: bridge
    internal: true
```

## Resource Limits

```yaml
services:
  app:
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.25'
          memory: 256M
```

## Health Checks

```yaml
services:
  app:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Container Signing

```bash
# Cosign
cosign generate-key-pair
cosign sign myimage:latest

# Verify
cosign verify myimage:latest
```

## Runtime Security

```bash
# gVisor
docker run --runtime=runsc myapp

# Kata Containers
docker run --runtime=kata-runtime myapp
```

## Dockerfile Security

```dockerfile
# Use specific version
FROM python:3.12-slim-bookworm@sha256:...

# No secrets in image
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Clean up
RUN apt-get clean && rm -rf /var/lib/apt/lists/*

# Non-root user
USER 1000
```

## Security Checklist

- [ ] Run as non-root
- [ ] Use read-only filesystem
- [ ] Drop capabilities
- [ ] Scan images for vulnerabilities
- [ ] Limit resources
- [ ] Use secrets management
- [ ] Network isolation
- [ ] Health checks
- [ ] Sign images
- [ ] Regular updates
