# TinyLlama Fast API (Node.js)

A lightweight Node.js Express API server for TinyLlama model via Ollama optimized for fast responses and streaming on Jetson AGX Orin.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Implementation](#api-implementation)
- [API Reference](#api-reference)
- [Client Examples](#client-examples)
- [Troubleshooting](#troubleshooting)

## Prerequisites

| Component | Requirement |
|-----------|-------------|
| Node.js | 18+ |
| Ollama | Installed |
| Model | tinyllama |

## Installation

```bash
npm install express ollama
```

## Quick Start

```bash
node fast_api.js
```

## API Implementation

```javascript
const express = require('express');
const { Ollama } = require('ollama');

const app = express();
const ollama = new Ollama();

app.use(express.json());

const MODEL = 'tinyllama';

/**
 * Quick response endpoint
 * POST /api/quick
 */
app.post('/api/quick', async (req, res) => {
    try {
        const { prompt, temperature = 0.8, max_tokens = 256 } = req.body;
        
        if (!prompt) {
            return res.status(400).json({ error: 'Prompt is required' });
        }
        
        const response = await ollama.generate({
            model: MODEL,
            prompt,
            options: { temperature, num_predict: max_tokens }
        });
        
        res.json({ 
            response: response.response,
            model: MODEL
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

/**
 * Streaming endpoint
 * POST /api/stream
 */
app.post('/api/stream', async (req, res) => {
    try {
        const { prompt, temperature = 0.8 } = req.body;
        
        res.setHeader('Content-Type', 'text/event-stream');
        res.setHeader('Cache-Control', 'no-cache');
        res.setHeader('Connection', 'keep-alive');
        
        const stream = await ollama.generate({
            model: MODEL,
            prompt,
            options: { temperature },
            stream: true
        });
        
        for await (const chunk of stream) {
            res.write(chunk.response);
        }
        res.end();
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

/**
 * Chat endpoint
 * POST /api/chat
 */
app.post('/api/chat', async (req, res) => {
    try {
        const { message } = req.body;
        
        const response = await ollama.chat({
            model: MODEL,
            messages: [{ role: 'user', content: message }]
        });
        
        res.json({ 
            reply: response.message.content,
            model: MODEL
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
    res.json({ status: 'ok', model: MODEL });
});

const PORT = process.env.PORT || 3005;

app.listen(PORT, () => {
    console.log(`TinyLlama fast API on port ${PORT}`);
});
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/quick | Quick generation |
| POST | /api/stream | Streaming |
| POST | /api/chat | Chat |
| GET | /health | Health check |

### Examples

```bash
# Quick
curl -X POST http://localhost:3005/api/quick \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Hello!"}'

# Stream
curl -X POST http://localhost:3005/api/stream \
    -H "Content-Type: application/json" \
    -d '{"prompt": "Count to 5"}'
```

## Client Examples

### JavaScript

```javascript
// Quick
const response = await fetch('http://localhost:3005/api/quick', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt: 'Hello!' })
});
const data = await response.json();
console.log(data.response);

// Stream
const streamRes = await fetch('http://localhost:3005/api/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt: 'Count to 5' })
});
const reader = streamRes.body.getReader();
while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    console.log(new TextDecoder().decode(value));
}
```

## Troubleshooting

```bash
ollama pull tinyllama
```

## See Also

- [Ollama](https://github.com/ollama/ollama)
- [Part 13 Python](./python/tinyllama-chat.md)
