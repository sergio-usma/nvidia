# Docker Networking

This guide covers Docker networking on Jetson AGX Orin, including network modes, port forwarding, and custom networks.

## Network Modes

- **bridge**: Default, for standalone containers
- **host**: Removes network isolation
- **none**: Disables networking
- **container**: Shares network with another container

## List Networks

```bash
docker network ls
```

## Create Custom Network

```bash
docker network create jetson-net
```

## Run Container with Network

```bash
docker run --network jetson-net -d nginx
```

## Port Mapping

Map container port to host:

```bash
docker run -p 8080:80 nginx
```

Multiple ports:

```bash
docker run -p 8080:80 -p 8443:443 nginx
```

## Bridge Network Configuration

View bridge:

```bash
docker network inspect bridge
```

Create custom bridge with subnet:

```bash
docker network create --subnet=172.20.0.0/16 jetson-bridge
```

## Host Network Mode

```bash
docker run --network host nginx
```

## Macvlan Networks

For direct network access:

```bash
docker network create -d macvlan \
  --subnet=192.168.1.0/24 \
  --gateway=192.168.1.1 \
  -o parent=eth0 jetson-macvlan
```

## Container Communication

### Link containers (legacy)

```bash
docker run --link db:db web
```

### Network-based communication

```bash
docker network create app-net

# Start database
docker run -d --name db --network app-net postgres

# Start app
docker run -d --name web --network app-net -e DB_HOST=db webapp
```

## DNS Configuration

Use custom DNS:

```bash
docker run --dns 8.8.8.8 nginx
```

Or in docker-compose:

```yaml
services:
  app:
    dns:
      - 8.8.8.8
      - 8.8.4.4
```

## Portainer for Network Management

```bash
docker run -d -p 9000:9000 \
  --name portainer \
  --restart always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  portainer/portainer
```

Access at http://jetson:9000

## Network Troubleshooting

### Check container networking

```bash
docker exec container_name ip addr
docker exec container_name ping google.com
```

### View container ports

```bash
docker port container_name
```

### DNS resolution issues

```bash
docker exec container_name nslookup google.com
```

## Advanced: Traefik Reverse Proxy

```yaml
version: '3.8'
services:
  traefik:
    image: traefik:v2.10
    ports:
      - "80:80"
      - "443:443"
      - "8080:8080"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./traefik.yml:/traefik.yml:ro
    networks:
      - app-net

  ollama:
    image: ollama/ollama:latest
    networks:
      - app-net
    labels:
      - "traefik.http.routers.ollama.rule=Host(`ollama.local`)"

networks:
  app-net:
    driver: bridge
```

## IPv6 Support

Enable in daemon:

```bash
sudo nano /etc/docker/daemon.json
```

```json
{
  "ipv6": true,
  "ip6tables": true
}
```

```bash
sudo systemctl restart docker
```
