# Nemotron 120B llama.cpp Node.js

A Node.js Express API server for interacting with NVIDIA Nemotron 120B model served via llama.cpp HTTP server on Jetson AGX Orin.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Implementation](#api-implementation)
- [API Reference](#api-reference)
- [Error Handling](#error-handling)
- [Production](#production)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

| Component | Requirement |
|-----------|-------------|
| Node.js | 18+ |
| llama.cpp | With CUDA support |
| Model | Nemotron 120B GGUF |

### Verify Setup

```bash
node --version
npm --version
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Nemotron Node.js API Server                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Express     │  │ axios       │  │ llama.cpp    │  │
│  │ Server      │  │ Client      │  │ Integration  │  │
│  └──────────────┘  └──────────────┘  └────────────────┘  │
└─────────────────────────┬────────────────────────────────────┘
                          │ HTTP
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              llama.cpp Server + Nemotron 120B              │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Install Dependencies

```bash
npm install express axios
```

## Quick Start

### Start llama.cpp Server

```bash
llama-cli \
    -m ~/Nemotron-Super-GGUF/Nemotron-120B.gguf \
    -ngl 99 \
    -c 2048 \
    --server \
    --port 8080
```

### Start Node.js API

```bash
node nemotron_llama.js
```

## API Implementation

```javascript
const express = require('express');
const axios = require('axios');

const app = express();
app.use(express.json());

const LLAMA_SERVER = 'http://localhost:8080';

/**
 * Ask a question to Nemotron
 * POST /ask
 * Body: { question: string }
 */
app.post('/ask', async (req, res) => {
    try {
        const { question } = req.body;
        
        if (!question) {
            return res.status(400).json({ error: 'Question is required' });
        }
        
        const response = await axios.post(`${LLAMA_SERVER}/completion`, {
            prompt: `Question: ${question}\nAnswer:`,
            n_predict: 2048,
            temperature: 0.5,
            stream: false
        });
        
        res.json({ 
            answer: response.data.content,
            model: 'nemotron-120b'
        });
    } catch (error) {
        console.error('Error:', error.message);
        res.status(500).json({ error: error.message });
    }
});

/**
 * Generate with custom parameters
 * POST /generate
 */
app.post('/generate', async (req, res) => {
    try {
        const { prompt, temperature = 0.7, max_tokens = 1024 } = req.body;
        
        const response = await axios.post(`${LLAMA_SERVER}/completion`, {
            prompt,
            n_predict: max_tokens,
            temperature,
            top_p: 0.9,
            repeat_penalty: 1.1
        });
        
        res.json({ 
            response: response.data.content,
            model: 'nemotron-120b'
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

/**
 * Health check
 * GET /health
 */
app.get('/health', (req, res) => {
    res.json({ status: 'ok', model: 'nemotron-120b' });
});

const PORT = process.env.PORT || 4003;

app.listen(PORT, () => {
    console.log(`Nemotron 120B API running on port ${PORT}`);
});
```

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /ask | Ask a question |
| POST | /generate | Generate with custom params |
| GET | /health | Health check |

### Request/Response Examples

#### POST /ask

```bash
curl -X POST http://localhost:4003/ask \
    -H "Content-Type: application/json" \
    -d '{"question": "What is machine learning?"}'
```

Response:
```json
{
  "answer": "Machine learning is...",
  "model": "nemotron-120b"
}
```

#### POST /generate

```bash
curl -X POST http://localhost:4003/generate \
    -H "Content-Type: application/json" \
    -d '{
        "prompt": "Write a poem about AI",
        "temperature": 0.8,
        "max_tokens": 500
    }'
```

## Error Handling

```javascript
app.post('/ask', async (req, res) => {
    try {
        const { question } = req.body;
        
        if (!question) {
            return res.status(400).json({ 
                error: 'Validation error',
                message: 'Question is required'
            });
        }
        
        const response = await axios.post(`${LLAMA_SERVER}/completion`, {
            prompt: `Question: ${question}\nAnswer:`,
            n_predict: 2048
        });
        
        res.json({ answer: response.data.content });
    } catch (error) {
        if (error.code === 'ECONNREFUSED') {
            return res.status(503).json({ 
                error: 'Service unavailable',
                message: 'llama.cpp server not running'
            });
        }
        
        res.status(500).json({ 
            error: 'Internal server error',
            message: error.message 
        });
    }
});
```

## Production

### Using PM2

```bash
# Install PM2
npm install -g pm2

# Start with PM2
pm2 start nemotron_llama.js --name nemotron-api

# Auto-restart on crashes
pm2 start nemotron_llama.js --name nemotron-api --watch

# View logs
pm2 logs nemotron-api
```

### Using Docker

```dockerfile
FROM node:18-alpine

WORKDIR /app
COPY nemotron_llama.js .
RUN npm install express axios

EXPOSE 4003

CMD ["node", "nemotron_llama.js"]
```

## Troubleshooting

### Connection Refused

```bash
# Check llama.cpp server
curl http://localhost:8080/health

# Start server if not running
llama-cli -m model.gguf -ngl 99 --server
```

### Out of Memory

```bash
# Reduce GPU layers
-ngl 40

# Reduce context
-c 2048
```

### Slow Responses

```bash
# Check GPU utilization
nvtop
```

## See Also

- [llama.cpp](https://github.com/ggerganov/llama.cpp)
- [Part 13 Python](./python/nemotron-super.md)
