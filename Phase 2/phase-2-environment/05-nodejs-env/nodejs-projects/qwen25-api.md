# Qwen 3.5 27B llama.cpp Node.js

A Node.js Express API server for Qwen 2.5 27B model via llama.cpp HTTP server on Jetson AGX Orin.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Implementation](#api-implementation)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)

## Prerequisites

| Component | Requirement |
|-----------|-------------|
| Node.js | 18+ |
| llama.cpp | With CUDA |
| Model | Qwen 2.5 27B GGUF |

## Installation

```bash
npm install express axios
```

## Quick Start

```bash
# Start llama.cpp server
llama-cli -m ~/models/Qwen2.5-27B.gguf -ngl 99 -c 4096 --server

# Start API
node qwen25_api.js
```

## API Implementation

```javascript
const express = require('express');
const axios = require('axios');

const app = express();
app.use(express.json());

const LLAMA_SERVER = 'http://localhost:8080';

/**
 * Chat endpoint
 * POST /chat
 */
app.post('/chat', async (req, res) => {
    try {
        const { message, temperature = 0.7, max_tokens = 512 } = req.body;
        
        if (!message) {
            return res.status(400).json({ error: 'Message is required' });
        }
        
        const response = await axios.post(`${LLAMA_SERVER}/completion`, {
            prompt: `User: ${message}\nAssistant:`,
            n_predict: max_tokens,
            temperature,
            stream: false
        });
        
        res.json({ 
            reply: response.data.content,
            model: 'qwen2.5-27b'
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
        
        const response = await axios.post(`${LLAMA_SERVER}/completion`, {
            prompt,
            n_predict: max_tokens,
            temperature,
            top_p: 0.9,
            repeat_penalty: 1.1
        });
        
        res.json({ response: response.data.content });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

/**
 * Code generation
 * POST /code
 */
app.post('/code', async (req, res) => {
    try {
        const { task, language = 'python' } = req.body;
        
        const response = await axios.post(`${LLAMA_SERVER}/completion`, {
            prompt: `Write ${language} code for: ${task}`,
            n_predict: 1024,
            temperature: 0.2
        });
        
        res.json({ code: response.data.content, language });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

/**
 * Health check
 * GET /health
 */
app.get('/health', (req, res) => {
    res.json({ status: 'ok', model: 'qwen2.5-27b' });
});

const PORT = process.env.PORT || 4001;

app.listen(PORT, () => {
    console.log(`Qwen 3.5 API on port ${PORT}`);
});
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /chat | Chat interaction |
| POST | /generate | Text generation |
| POST | /code | Code generation |
| GET | /health | Health check |

## Examples

```bash
# Chat
curl -X POST http://localhost:4001/chat \
    -H "Content-Type: application/json" \
    -d '{"message": "What is Python?"}'

# Code
curl -X POST http://localhost:4001/code \
    -H "Content-Type: application/json" \
    -d '{"task": "hello world", "language": "python"}'
```

## Troubleshooting

```bash
# Check llama.cpp
curl http://localhost:8080/health
```

## See Also

- [llama.cpp](https://github.com/ggerganov/llama.cpp)
