# Part 24: Hybrid Systems & SaaS Deployment with Local AI

## Overview

This section covers strategies for building hybrid AI systems that combine local inference with cloud connectivity, enabling SaaS deployment, advanced automation with n8n, and seamless integration with external services - all running on your Jetson AGX Orin.

## Available Guides

| File | Description |
|------|-------------|
| [01-overview.md](./01-overview.md) | Hybrid AI architectures introduction |
| [02-network-architecture.md](./02-network-architecture.md) | Network setup and configuration |
| [03-api-server.md](./03-api-server.md) | Building APIs with local models |
| [04-saas-deployment.md](./04-saas-deployment.md) | Deploying SaaS from Jetson |
| [05-reverse-proxy.md](./05-reverse-proxy.md) | Nginx, SSL, and domain setup |
| [06-webhooks.md](./06-webhooks.md) | Webhook-based automation |
| [07-n8n-advanced.md](./07-n8n-advanced.md) | Advanced n8n workflows |
| [08-external-services.md](./08-external-services.md) | Connecting to APIs |
| [09-automation-patterns.md](./09-automation-patterns.md) | Advanced automation patterns |
| [10-monitoring.md](./10-monitoring.md) | System monitoring |
| [11-security.md](./11-security.md) | Security best practices |
| [12-scaling.md](./12-scaling.md) | Performance and scaling |
| [13-troubleshooting.md](./13-troubleshooting.md) | Common issues |

## Quick Start

```bash
# 1. Start Ollama API server
ollama serve

# 2. Create API endpoint
python3 api_server.py

# 3. Connect to n8n
# Create webhook in n8n → point to Jetson IP
```

## Prerequisites

- Jetson AGX Orin 64GB
- JetPack 6.2.2
- Domain name (for SaaS)
- n8n (see Part 21)
- Ollama/llama.cpp running

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Internet                                 │
│         │                    │                    │          │
│         ▼                    ▼                    ▼          │
│   ┌──────────┐        ┌──────────┐        ┌──────────┐   │
│   │ External  │        │  n8n     │        │  Cloud   │   │
│   │   APIs    │        │Workflows │        │ Services │   │
│   └─────┬─────┘        └────┬─────┘        └────┬─────┘   │
│         │                   │                   │          │
│         └───────────────────┼───────────────────┘          │
│                             │                              │
│                             ▼                              │
│                   ┌─────────────────────┐                   │
│                   │   Reverse Proxy     │                   │
│                   │   (Nginx + SSL)    │                   │
│                   └──────────┬──────────┘                   │
│                              │                              │
│                              ▼                              │
│  ┌─────────────────────────────────────────────────────┐  │
│  │              Jetson AGX Orin                         │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐        │  │
│  │  │ Ollama   │  │  FastAPI │  │  RAG    │        │  │
│  │  │   API    │  │   Server │  │ Pipeline │        │  │
│  │  └──────────┘  └──────────┘  └──────────┘        │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Next Steps

Start with [01-overview.md](./01-overview.md) to understand hybrid architectures.
