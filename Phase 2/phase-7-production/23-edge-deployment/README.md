# Part 27: Deploy AI Projects - Online, Offline & Private Networks

## Overview

This section covers deployment strategies for AI projects on Jetson AGX Orin across different network scenarios: online (cloud-connected), offline (air-gapped), and private networks (enterprise/secure environments).

## Available Guides

| File | Description |
|------|-------------|
| [01-overview.md](./01-overview.md) | Deployment strategies overview |
| [02-network-modes.md](./02-network-modes.md) | Online, offline, private network concepts |
| [03-local-deployment.md](./03-local-deployment.md) | Local network deployment |
| [04-offline-deployment.md](./04-offline-deployment.md) | Air-gapped/offline deployment |
| [05-private-network.md](./05-private-network.md) | Enterprise private network setup |
| [06-docker-containers.md](./06-docker-containers.md) | Container deployment |
| [07-reverse-proxy.md](./07-reverse-proxy.md) | Nginx, SSL, domain setup |
| [08-authentication.md](./08-authentication.md) | API keys, OAuth, security |
| [09-backup-recovery.md](./09-backup-recovery.md) | Backup and disaster recovery |
| [10-scaling.md](./10-scaling.md) | Multi-device deployment |
| [11-monitoring.md](./11-monitoring.md) | Deployment monitoring |
| [12-troubleshooting.md](./12-troubleshooting.md) | Common deployment issues |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Deployment Scenarios                         │
├─────────────────┬─────────────────┬─────────────────────────┤
│     ONLINE      │    OFFLINE      │    PRIVATE NETWORK     │
│  (Cloud)       │  (Air-gapped)   │   (Enterprise)        │
├─────────────────┼─────────────────┼─────────────────────────┤
│ • Public APIs  │ • No internet   │ • Internal network    │
│ • Cloud sync   │ • Air-gapped    │ • VPN required        │
│ • Updates      │ • Isolated      │ • Firewall rules      │
│ • CDN          │ • Secure        │ • Proxy              │
└─────────────────┴─────────────────┴─────────────────────────┘
```

## Prerequisites

- Jetson AGX Orin 64GB
- JetPack 6.2.2
- Ollama or llama.cpp running
- Network configuration access

## Next Steps

Start with [01-overview.md](./01-overview.md) to understand deployment strategies.
