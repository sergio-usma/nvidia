# Docker Compose

Docker Compose lets you define and run multi-container applications.

## Install Docker Compose

Check if already installed:

```bash
docker-compose --version
```

If not, install:

```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## Basic docker-compose.yml Structure

```yaml
version: '3.8'

services:
  service_name:
    image: image_name:tag
    runtime: nvidia
    ports:
      - "host_port:container_port"
    volumes:
      - ./local_folder:/container_folder
    restart: unless-stopped
```

## Example: Ollama + Open WebUI

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  ollama:
    image: dustynv/ollama:r36.5.0
    container_name: ollama
    runtime: nvidia
    ports:
      - "11434:11434"
    volumes:
      - ./ollama_storage:/root/.ollama
    restart: unless-stopped
    networks:
      - ai-net

  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: open-webui
    ports:
      - "3000:8080"
    volumes:
      - ./open-webui_data:/app/backend/data
    environment:
      - OLLAMA_BASE_URL=http://ollama:11434
    restart: unless-stopped
    networks:
      - ai-net
    depends_on:
      - ollama

networks:
  ai-net:
    driver: bridge
```

## Common Commands

| Command | Description |
|---------|-------------|
| `docker-compose up -d` | Start all services in background |
| `docker-compose down` | Stop and remove containers |
| `docker-compose ps` | Show service status |
| `docker-compose logs -f` | View logs |
| `docker-compose restart` | Restart all services |
| `docker-compose pull` | Pull latest images |
| `docker-compose build` | Build images |

## Key Options Explained

- `runtime: nvidia` - Enable GPU access
- `restart: unless-stopped` - Auto-start on boot
- `depends_on` - Start order (doesn't wait for readiness)
- `volumes` - Persist data across container restarts
- `networks` - Container communication

## Access Services

After starting:
- Ollama API: `http://localhost:11434`
- Open WebUI: `http://localhost:3000`

## Clean Up with Compose

```bash
# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Stop and remove images
docker-compose down --rmi all
```

## Next Steps

- [jetson-containers](03-jetson-containers.md) - Use pre-built AI containers
- [Part 5: Running LLMs](../part-5-llms/01-ollama-setup.md) - Set up Ollama
