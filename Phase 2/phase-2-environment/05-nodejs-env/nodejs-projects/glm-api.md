# GLM-4.7 Flash Node.js Fast API

A Node.js Express API server for GLM-4.7 Flash model via Ollama with chat and summarization endpoints on Jetson AGX Orin.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
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
| Model | glm-4.7-flash |

### Verify Setup

```bash
node --version
ollama list
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              GLM Flash Node.js API Server                   │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Express     │  │ Ollama      │  │ Chat         │  │
│  │ Server      │  │ SDK         │  │ Handler      │  │
│  └──────────────┘  └──────────────┘  └────────────────┘  │
└─────────────────────────┬────────────────────────────────────┘
                          │ Ollama API
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Ollama Server + GLM-4.7 Flash                 │
└─────────────────────────────────────────────────────────────┘
```

## Installation

### Install Dependencies

```bash
npm install express ollama
```

## Quick Start

```bash
# Start Ollama
ollama serve

# Pull model
ollama pull glm-4.7-flash

# Start API
node glm_api.js
```

## API Implementation

```javascript
const express = require('express');
const { Ollama } = require('ollama');

const app = express();
const ollama = new Ollama();

app.use(express.json());

const MODEL = 'glm-4.7-flash';

/**
 * Chat endpoint
 * POST /chat
 */
app.post('/chat', async (req, res) => {
    try {
        const { message, temperature = 0.7 } = req.body;
        
        if (!message) {
            return res.status(400).json({ error: 'Message is required' });
        }
        
        const response = await ollama.chat({
            model: MODEL,
            messages: [{ role: 'user', content: message }],
            options: { temperature }
        });
        
        res.json({ 
            reply: response.message.content,
            model: MODEL
        });
    } catch (error) {
        console.error('Error:', error);
        res.status(500).json({ error: error.message });
    }
});

/**
 * Summarization endpoint
 * POST /summary
 */
app.post('/summary', async (req, res) => {
    try {
        const { text, max_words = 100 } = req.body;
        
        if (!text) {
            return res.status(400).json({ error: 'Text is required' });
        }
        
        const prompt = `Summarize in about ${max_words} words:\n\n${text}`;
        
        const response = await ollama.generate({
            model: MODEL,
            prompt
        });
        
        res.json({ 
            summary: response.response,
            model: MODEL
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

/**
 * Generate endpoint
 * POST /generate
 */
app.post('/generate', async (req, res) => {
    try {
        const { prompt, temperature = 0.7, max_tokens = 512 } = req.body;
        
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
 * Multi-turn chat
 * POST /chat/multi
 */
app.post('/chat/multi', async (req, res) => {
    try {
        const { messages } = req.body;
        
        const response = await ollama.chat({
            model: MODEL,
            messages
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
app.get('/health', async (req, res) => {
    try {
        // Check if model is available
        const models = await ollama.list();
        const hasModel = models.models.some(m => m.name === MODEL);
        
        res.json({ 
            status: 'ok', 
            model: MODEL,
            available: hasModel
        });
    } catch (error) {
        res.status(500).json({ status: 'error', error: error.message });
    }
});

const PORT = process.env.PORT || 3023;

app.listen(PORT, () => {
    console.log(`GLM Flash API running on port ${PORT}`);
});
```

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /chat | Chat interaction |
| POST | /summary | Text summarization |
| POST | /generate | Text generation |
| POST | /chat/multi | Multi-turn chat |
| GET | /health | Health check |

### Request Examples

#### POST /chat

```bash
curl -X POST http://localhost:3023/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "What is Python?"}'
```

```javascript
// JavaScript client
const response = await fetch('http://localhost:3023/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: 'What is Python?' })
});
const data = await response.json();
console.log(data.reply);
```

#### POST /summary

```bash
curl -X POST http://localhost:3023/summary \
    -H "Content-Type: application/json" \
    -d '{"text": "Long text to summarize...", "max_words": 50}'
```

## Client Examples

### Python

```python
import requests

url = "http://localhost:3023/chat"
data = {"message": "Hello!"}
response = requests.post(url, json=data)
print(response.json()["reply"])
```

### JavaScript (Browser)

```javascript
const response = await fetch('http://localhost:3023/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: 'Hello!' })
});
const data = await response.json();
console.log(data.reply);
```

## Troubleshooting

### Model Not Found

```bash
# Pull model
ollama pull glm-4.7-flash

# Check models
ollama list
```

### Connection Error

```bash
# Start Ollama
ollama serve
```

## See Also

- [Ollama](https://github.com/ollama/ollama)
- [Part 13 Python](./python/glm-flash.md)
