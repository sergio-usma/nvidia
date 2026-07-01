# Container Orchestration

This guide covers container orchestration with Docker Swarm and Kubernetes on Jetson AGX Orin.

## Docker Swarm Basics

```bash
# Initialize swarm
docker swarm init --advertise-addr 192.168.1.100

# Join as worker
docker swarm join --token SWMTKN-1-xxx 192.168.1.100:2377

# Leave swarm
docker swarm leave --force
```

## Services

```bash
# Create service
docker service create --name myapp --replicas 3 -p 8080:80 nginx

# List services
docker service ls

# Scale service
docker service scale myapp=5

# Update service
docker service update --image nginx:latest myapp

# Remove service
docker service rm myapp
```

## Stacks

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    image: nginx
    deploy:
      replicas: 3
    ports:
      - "80:80"
    volumes:
      - ./html:/usr/share/nginx/html

  api:
    image: myapi
    deploy:
      replicas: 2
    environment:
      - DATABASE_URL=postgres://db:5432/app

  db:
    image: postgres
    volumes:
      - db-data:/var/lib/postgresql/data

volumes:
  db-data:
```

```bash
# Deploy stack
docker stack deploy -c docker-compose.yml myapp

# List stacks
docker stack ls

# Remove stack
docker stack rm myapp
```

## Health Checks

```yaml
services:
  api:
    image: myapi
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
```

## Secrets

```bash
# Create secret
echo "mypassword" | docker secret create db_password -

# Use in service
docker service create --secret db_password myapp
```

In docker-compose:

```yaml
services:
  db:
    image: postgres
    secrets:
      - db_password

secrets:
  db_password:
    external: true
```

## Networking

```bash
# Create overlay network
docker network create -d overlay mynetwork

# Use in service
docker service create --network mynetwork myapp
```

## Volumes

```bash
# Create volume
docker volume create mydata

# Use in service
docker service create --mount type=volume,source=mydata,target=/data myapp
```

## Troubleshooting

```bash
# List tasks
docker service ps myapp

# Inspect service
docker service inspect myapp

# View logs
docker service logs myapp

# Check node status
docker node ls
```

## Kubernetes on Jetson

Install k3s (lightweight):

```bash
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable=traefik" sh -
```

## kubectl Basics

```bash
# Check nodes
kubectl get nodes

# Get pods
kubectl get pods

# Get services
kubectl get services

# Apply config
kubectl apply -f deployment.yaml
```

## Deployment Example

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
      - name: myapp
        image: myimage:latest
        ports:
        - containerPort: 8080
        resources:
          limits:
            memory: "256Mi"
            cpu: "500m"
```

## Service

```yaml
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: myapp
spec:
  selector:
    app: myapp
  ports:
  - port: 80
    targetPort: 8080
  type: LoadBalancer
```

## ConfigMap

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: myconfig
data:
  config.json: |
    {
      "key": "value"
    }
```

## Scaling

```bash
# Scale deployment
kubectl scale deployment myapp --replicas=5

# Autoscale
kubectl autoscale deployment myapp --min=2 --max=10 --cpu-percent=80
```

## Monitoring

```bash
# Get pod logs
kubectl logs -f myapp-pod

# Describe pod
kubectl describe pod myapp-pod

# Exec into pod
kubectl exec -it myapp-pod -- /bin/bash
```

## Helm Charts

```bash
# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Add repo
helm repo add stable https://charts.helm.sh/stable
helm repo update

# Install chart
helm install myrelease stable/nginx-ingress

# List releases
helm list
```

## Portainer

```bash
# Install Portainer
docker volume create portainer_data
docker run -d -p 9000:9000 --name portainer --restart always -v /var/run/docker.sock:/var/run/docker.sock -v portainer_data:/data portainer/portainer
```

Access: http://jetson:9000
