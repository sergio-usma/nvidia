# Docker Compose Advanced Patterns

This guide covers advanced Docker Compose patterns for multi-container AI applications on Jetson AGX Orin.

## Service Dependencies

```yaml
version: '3.8'
services:
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama-data:/root/.ollama
    networks:
      - ai-net

  api:
    build: ./api
    depends_on:
      ollama:
        condition: service_healthy
    environment:
      - OLLAMA_HOST=ollama:11434
    networks:
      - ai-net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  web:
    build: ./web
    depends_on:
      - api
    ports:
      - "3000:3000"
    networks:
      - ai-net

networks:
  ai-net:
    driver: bridge
```

## Health Checks

```yaml
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: secret
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
```

## Resource Limits

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    deploy:
      resources:
        limits:
          memory: 16G
          cpus: '6'
        reservations:
          memory: 4G
          cpus: '2'
    volumes:
      - ollama-data:/root/.ollama
```

## Restart Policies

```yaml
services:
  api:
    image: myapi:latest
    restart: unless-stopped
    # Options: no, always, on-failure, unless-stopped
```

## Environment Variables

```yaml
services:
  api:
    image: myapi:latest
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgres://user:pass@db:5432/mydb
      - LOG_LEVEL=info
    env_file:
      - .env.production
```

## Secrets Management

```yaml
services:
  db:
    image: postgres:15
    secrets:
      - db_password
    environment:
      POSTGRES_PASSWORD_FILE: /run/secrets/db_password

secrets:
  db_password:
    file: ./secrets/db_password.txt
```

## Profiles

```yaml
services:
  app:
    image: myapp:latest

  development:
    image: myapp:dev
    profiles:
      - dev
    volumes:
      - ./src:/app/src

  testing:
    image: myapp:test
    profiles:
      - test
```

Run with profile: `docker-compose --profile dev up`

## Logging Configuration

```yaml
services:
  api:
    image: myapi:latest
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Network Configuration

```yaml
services:
  frontend:
    image: nginx
    networks:
      - frontend-net
      - backend-net

  backend:
    image: mybackend
    networks:
      - backend-net

networks:
  frontend-net:
    driver: bridge
  backend-net:
    internal: true
```

## Extending Services

```yaml
# docker-compose.base.yml
services:
  app:
    image: myapp:latest
    restart: unless-stopped

# docker-compose.override.yml
services:
  app:
    build: .
    volumes:
      - ./src:/app/src
    environment:
      - DEBUG=true
```

## Complete AI Stack Example

```yaml
version: '3.8'
services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    volumes:
      - ollama-models:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
    ports:
      - "11434:11434"
    networks:
      - ai-stack
    restart: unless-stopped

  faster-whisper:
    image::coder_ai/faster-whisper:latest
    container_name: faster-whisper
    ports:
      - "8001:8001"
    volumes:
      - whisper-models:/models
    networks:
      - ai-stack
    restart: unless-stopped

  piper:
    image: ghcr.io/mozilla/piper:latest
    container_name: piper
    ports:
      - "8002:5000"
    volumes:
      - piper-models:/models
    networks:
      - ai-stack
    restart: unless-stopped

  openwebui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: openwebui
    ports:
      - "8080:8080"
    environment:
      - OLLAMA_BASE_URLS=http://ollama:11434
      - WEBUI_SECRET_KEY=t0p-s3cr3t-passw0rd
    volumes:
      - openwebui-data:/app/backend/data
    networks:
      - ai-stack
    depends_on:
      - ollama
    restart: unless-stopped

networks:
  ai-stack:
    driver: bridge

volumes:
  ollama-models:
  whisper-models:
  piper-models:
  openwebui-data:
```

## Scaling Services

```bash
docker-compose up -d --scale ollama=3
```

## Development Workflow

```yaml
version: '3.8'
services:
  app:
    build:
      context: .
      target: development
    volumes:
      - .:/app
      - /app/node_modules
    environment:
      - NODE_ENV=development
    command: npm run dev

  app-prod:
    build:
      context: .
      target: production
    profiles:
      - production
```
