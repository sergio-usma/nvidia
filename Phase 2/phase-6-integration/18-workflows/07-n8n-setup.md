# n8n Setup for Jetson

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Ollama Integration](#ollama-integration)
4. [Workflow Examples](#workflow-examples)
5. [Webhooks](#webhooks)

## Introduction

n8n is a powerful workflow automation tool that can integrate with Ollama on Jetson to create AI-powered automations.

## Installation

### Option 1: Docker (Recommended)

```bash
# Install Docker if not present
sudo apt update
sudo apt install docker.io

# Run n8n container
docker run -it --name n8n \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  -e N8N_HOST=0.0.0.0 \
  -e N8N_PORT=5678 \
  -e N8N_PROTOCOL=http \
  n8nio/n8n:latest

# Access at http://jetson-ip:5678
```

### Option 2: npm

```bash
# Install Node.js 20.x
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

# Install n8n
npm install -g n8n

# Run n8n
n8n start

# Or as service
sudo systemctl enable n8n
```

### Option 3: Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  n8n:
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    volumes:
      - n8n_data:/home/node/.n8n
    environment:
      - N8N_HOST=0.0.0.0
      - N8N_PORT=5678
      - N8N_PROTOCOL=http

volumes:
  n8n_data:
```

```bash
docker-compose up -d
```

## Ollama Integration

### Using HTTP Request Node

1. Open n8n at http://jetson-ip:5678
2. Create new workflow
3. Add HTTP Request node
4. Configure:

```
Method: POST
URL: http://localhost:11434/api/generate
Body Content Type: JSON
Body:

{
  "model": "llama3.2:3b",
  "prompt": "{{ $json.prompt }}",
  "stream": false
}
```

### Custom n8n Node for Ollama

Create custom node:

```javascript
// ~/.n8n/custom/ollama.js
const https = require('https');

module.exports = class Ollama {
  constructor() {
    this.description = {
      displayName: 'Ollama',
      name: 'ollama',
      icon: 'file:ollama.svg',
      group: ['AI'],
      version: 1,
      description: 'Interact with Ollama models',
      defaults: {
        name: 'Ollama',
      },
      inputs: ['main'],
      outputs: ['main'],
      credentials: [
        {
          name: 'ollamaApi',
          required: true,
        },
      ],
      properties: [
        {
          displayName: 'Model',
          name: 'model',
          type: 'string',
          default: 'llama3.2:3b',
        },
        {
          displayName: 'Prompt',
          name: 'prompt',
          type: 'string',
          default: '',
        },
      ],
    };
  }

  async execute() {
    const items = this.getInputData();
    const credentials = await this.getCredentials('ollamaApi');
    const { model, prompt } = this.getNode().parameters;

    // Make request to Ollama
    const response = await this.helpers.request({
      method: 'POST',
      url: `${credentials.url}/api/generate`,
      body: {
        model,
        prompt,
        stream: false,
      },
      json: true,
    });

    return [[{ json: { response: response.response } }]];
  }
};
```

## Workflow Examples

### Simple Chat Workflow

```
[Webhook] → [Set Node] → [HTTP Request (Ollama)] → [Response]
```

1. **Webhook**: Receive incoming requests
2. **Set**: Extract prompt from webhook body
3. **HTTP Request**: Call Ollama API
4. **Response**: Return to caller

### RAG Workflow with n8n

```
[Webhook] → [HTTP Request (Search)] → [HTTP Request (Ollama)] → [Response]
```

```json
// Webhook input
{
  "question": "How to optimize Jetson?"
}

// Search in vector store first
// Then prompt Ollama with context
```

### Multi-Step AI Workflow

```
[Schedule] → [HTTP Request (Ollama - Generate)] 
           → [HTTP Request (Ollama - Refine)] 
           → [Slack/Discord Notification]
```

### Image Generation Workflow

```
[Webhook] → [Set (Prompt)] → [HTTP Request (Ollama)] → [HTTP Request (SD)]
```

### Voice Pipeline

```
[Webhook] → [Transcribe (Whisper API)] → [Ollama (LLM)] → [Piper TTS] → [Response]
```

## Webhooks

### Incoming Webhook

1. Add "Webhook" node
2. Set HTTP Method: POST
3. Set Path: `ai-agent`
4. Test with:

```bash
curl -X POST http://jetson-ip:5678/webhook/ai-agent \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello from webhook!"}'
```

### Outgoing Webhook

Use "HTTP Request" node to call external services:

```
Ollama → HTTP Request → Slack
```

## Advanced Configuration

### Environment Variables

```bash
# .env
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=yourpassword
N8N_HOST=0.0.0.0
N8N_PORT=5678
N8N_PROTOCOL=http
WEBHOOK_URL=http://your-jetson-ip:5678/
```

### SSL/TLS

```bash
# With nginx reverse proxy
sudo apt install nginx

# Create nginx config
sudo tee /etc/nginx/sites-available/n8n > /dev/null <<EOF
server {
    listen 443 ssl;
    server_name jetson.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:5678;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/n8n /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

## n8n with Ollama Nodes

### Community Nodes

```bash
# Install community nodes
cd ~/.n8n
npm install n8n-nodes-ollama

# Restart n8n
docker restart n8n
```

### Using Custom Credentials

Create Ollama credentials:

1. Go to Settings → Credentials
2. Add "Ollama API"
3. Set URL: http://localhost:11434

## Next Steps

- [LangGraph](./08-langgraph.md)
- [RAG Automation](./09-rag-automation.md)
