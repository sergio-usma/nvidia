# Mistral Node.js Chat API

A Node.js Express API server for Mistral models via Ollama with conversation history and system prompt support on Jetson AGX Orin.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Implementation](#api-implementation)
- [API Reference](#api-reference)
- [Client Examples](#client-examples)
- [Production](#production)
- [Troubleshooting](#troubleshooting)

## Prerequisites

| Component | Requirement |
|-----------|-------------|
| Node.js | 18+ |
| Ollama | Installed |
| Model | mistral, mistral-nemo, or mistrallite |

### Verify Setup

```bash
node --version
ollama list
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│              Mistral Node.js Chat API                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ Express     │  │ Ollama      │  │ History       │  │
│  │ Server      │  │ SDK         │  │ Manager       │  │
│  └──────────────┘  └──────────────┘  └────────────────┘  │
└─────────────────────────┬────────────────────────────────────┘
                          │ Ollama API
                          ▼
┌─────────────────────────────────────────────────────────────┐
│              Ollama Server + Mistral                       │
└─────────────────────────────────────────────────────────────┘
```

## Installation

```bash
npm install express ollama
```

## Quick Start

```bash
# Start API
node chat_server.js

# Chat
curl -X POST http://localhost:3004/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "Explain quantum computing"}'
```

## API Implementation

```javascript
const express = require('express');
const { Ollama } = require('ollama');

const app = express();
const ollama = new Ollama();

app.use(express.json());

const MODELS = ['mistral', 'mistral-nemo', 'mistrallite'];
let conversationHistory = [];

/**
 * Clear conversation history
 * POST /clear
 */
app.post('/clear', (req, res) => {
    conversationHistory = [];
    res.json({ status: 'cleared' });
});

/**
 * Set system prompt
 * POST /system
 */
app.post('/system', (req, res) => {
    const { prompt } = req.body;
    
    if (!prompt) {
        return res.status(400).json({ error: 'Prompt is required' });
    }
    
    conversationHistory = [{ role: 'system', content: prompt }];
    res.json({ status: 'set', prompt });
});

/**
 * Chat endpoint
 * POST /chat
 */
app.post('/chat', async (req, res) => {
    try {
        const { message, model = 'mistral', temperature = 0.7 } = req.body;
        
        if (!message) {
            return res.status(400).json({ error: 'Message is required' });
        }
        
        if (!MODELS.includes(model)) {
            return res.status(400).json({ 
                error: 'Invalid model',
                available: MODELS
            });
        }
        
        conversationHistory.push({ role: 'user', content: message });
        
        const response = await ollama.chat({
            model,
            messages: conversationHistory,
            options: { temperature }
        });
        
        const reply = response.message.content;
        conversationHistory.push({ role: 'assistant', content: reply });
        
        res.json({ 
            response: reply, 
            history: conversationHistory,
            model
        });
        
    } catch (error) {
        console.error('Error:', error);
        res.status(500).json({ error: error.message });
    }
});

/**
 * Generate without history
 * POST /generate
 */
app.post('/generate', async (req, res) => {
    try {
        const { prompt, model = 'mistral', temperature = 0.7 } = req.body;
        
        const response = await ollama.generate({
            model,
            prompt,
            options: { temperature }
        });
        
        res.json({ 
            response: response.response,
            model
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

/**
 * List available models
 * GET /models
 */
app.get('/models', (req, res) => {
    res.json({ models: MODELS });
});

/**
 * Health check
 * GET /health
 */
app.get('/health', (req, res) => {
    res.json({ 
        status: 'ok',
        models: MODELS,
        history_length: conversationHistory.length
    });
});

const PORT = process.env.PORT || 3004;

app.listen(PORT, () => {
    console.log(`Mistral chat on port ${PORT}`);
    console.log(`Available models: ${MODELS.join(', ')}`);
});
```

## API Reference

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /chat | Chat with history |
| POST | /clear | Clear history |
| POST | /system | Set system prompt |
| POST | /generate | Generate without history |
| GET | /models | List models |
| GET | /health | Health check |

### Examples

#### Basic Chat

```bash
curl -X POST http://localhost:3004/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "Explain quantum computing"}'
```

#### Multi-turn

```bash
# First message
curl -X POST http://localhost:3004/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "What is Python?"}'

# Second message (continues conversation)
curl -X POST http://localhost:3004/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "What are its main features?"}'
```

#### System Prompt

```bash
curl -X POST http://localhost:3004/system \
    -H "Content-Type: application/json" \
    -d '{"prompt": "You are a helpful coding assistant."}'
```

#### Clear History

```bash
curl -X POST http://localhost:3004/clear
```

## Client Examples

### Python

```python
import requests

def chat(message):
    response = requests.post(
        'http://localhost:3004/chat',
        json={'message': message}
    )
    return response.json()['response']

print(chat("Hello!"))
```

### JavaScript

```javascript
async function chat(message) {
    const response = await fetch('http://localhost:3004/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message })
    });
    const data = await response.json();
    return data.response;
}

chat("Hello!").then(console.log);
```

## Production

### Using PM2

```bash
npm install -g pm2
pm2 start chat_server.js --name mistral-chat
pm2 logs mistral-chat
```

## Troubleshooting

```bash
# Check models
ollama list

# Pull missing model
ollama pull mistral
```

## See Also

- [Ollama](https://github.com/ollama/ollama)
- [Part 13 Python](./python/mistral-chat.md)
