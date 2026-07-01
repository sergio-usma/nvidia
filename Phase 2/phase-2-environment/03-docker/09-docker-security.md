# Docker Security Best Practices

This guide covers Docker security hardening for Jetson AGX Orin deployments.

## Run as Non-Root User

```dockerfile
FROM python:3.12-slim

RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app
COPY --chown=appuser:appgroup . .

USER appuser

CMD ["python", "app.py"]
```

## Build with BuildKit

Enable BuildKit:

```bash
export DOCKER_BUILDKIT=1
```

Or enable in daemon:

```bash
sudo nano /etc/docker/daemon.json
```

```json
{
  "features": {
    "buildkit": true
  }
}
```

## Scan Images for Vulnerabilities

Using Docker Scout:

```bash
docker scout cves myimage:latest
```

Using Trivy:

```bash
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
    aquasec/trivy image myimage:latest
```

## Limit Container Capabilities

Drop all capabilities, add only what's needed:

```bash
docker run --cap-drop ALL --cap-add NET_BIND_SERVICE myimage
```

## Use Read-Only Root Filesystem

```bash
docker run --read-only myimage
```

With tmpfs for write needs:

```bash
docker run --read-only --tmpfs /tmp myimage
```

## Restrict Network Access

```bash
# No network
docker run --network none myimage

# Internal network only
docker run --network internal-net myimage
```

## Secrets Management

Never store secrets in images:

```bash
# Bad
ENV API_KEY=secret

# Good - use runtime secret
docker run -e API_KEY=$API_KEY myimage
```

Or use Docker secrets:

```yaml
services:
  db:
    image: postgres:15
    secrets:
      - db_password

secrets:
  db_password:
    file: ./secrets/db_password
```

## Image Signing

Sign images with Cosign:

```bash
# Generate key pair
cosign generate-key-pair

# Sign image
cosign sign myimage:latest

# Verify
cosign verify myimage:latest
```

## Rate Limiting

```bash
# Pull rate limit
docker pull myimage:latest
# Add authentication for higher limits
docker login
docker pull myimage:latest
```

## Container Isolation

Use gVisor for stronger isolation:

```bash
docker run --runtime=runsc myimage
```

Or useKata Containers:

```bash
docker run --runtime=kata-runtime myimage
```

## Security Audit

Docker Bench:

```bash
docker run --rm -it \
    --privileged \
    -v /var/run/docker.sock:/var/run/docker.sock \
    docker/docker-bench-security
```

## Best Practices Summary

1. **Base image**: Use minimal images (alpine, slim)
2. **No root**: Run as non-root user
3. **Read-only**: Use read-only filesystem
4. **Limited capabilities**: Drop all capabilities
5. **No secrets in image**: Use runtime secrets
6. **Scan regularly**: Check for vulnerabilities
7. **Update base images**: Keep base image updated
8. **Multi-stage builds**: Reduce attack surface

## Dockerfile Security Template

```dockerfile
# Build stage
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Production stage
FROM gcr.io/distroless/python3-debian12

COPY --from=builder /root/.local /root/.local

WORKDIR /app
COPY --chown=nonroot:nonroot . .

USER nonroot

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["python", "main.py"]
```

## Docker Daemon Security

Edit daemon configuration:

```bash
sudo nano /etc/docker/daemon.json
```

```json
{
  "storage-driver": "overlay2",
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  },
  "live-restore": true,
  "userland-proxy": false,
  "icc": false,
  "no-new-privileges": true
}
```

## Runtime Security Flags

Always use:

```bash
docker run \
    --no-new-privileges \
    --security-opt=no-new-privileges:true \
    --cap-drop ALL \
    --read-only \
    myimage
```
