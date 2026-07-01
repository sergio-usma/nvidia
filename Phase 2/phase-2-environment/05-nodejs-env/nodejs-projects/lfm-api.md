# LFM2.5 Node.js API

A Node.js Express API server for LFM2.5 Thinking model via Ollama with chain-of-thought reasoning endpoints on Jetson AGX Orin.

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
| Ollama | Installed |
| Model | lfm2.5-thinking |

## Installation

```bash
npm install express ollama
```

## Quick Start

```bash
node lfm_api.js
```

## API Implementation

```javascript
const express = require('express');
const { Ollama } = require('ollama');

const app = express();
const ollama = new Ollama();

app.use(express.json());

const MODEL = 'lfm2.5-thinking';

/**
 * Chain-of-thought reasoning
 * POST /think
 */
app.post('/think', async (req, res) => {
    try {
        const { problem, temperature = 0.5 } = req.body;
        
        if (!problem) {
            return res.status(400).json({ error: 'Problem is required' });
        }
        
        const response = await ollama.generate({
            model: MODEL,
            prompt: `Think step by step: ${problem}`,
            options: { temperature, num_predict: 2048 }
        });
        
        res.json({ 
            thinking: response.response,
            model: MODEL
        });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

/**
 * Analyze topic
 * POST /analyze
 */
app.post('/analyze', async (req, res) => {
    try {
        const { topic } = req.body;
        
        const response = await ollama.generate({
            model: MODEL,
            prompt: `Analyze: ${topic}`
        });
        
        res.json({ analysis: response.response });
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

/**
 * Compare items
 * POST /compare
 */
app.post('/compare', async (req, res) => {
    try {
        const { item1, item2 } = req.body;
        
        const response = await ollama.generate({
            model: MODEL,
            prompt: `Compare: ${item1} vs ${item2}`
        });
        
        res.json({ comparison: response.response });
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

const PORT = process.env.PORT || 3017;

app.listen(PORT, () => {
    console.log(`LFM API on port ${PORT}`);
});
```

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /think | Chain-of-thought |
| POST | /analyze | Analyze topic |
| POST | /compare | Compare items |
| GET | /health | Health check |

## Example

```bash
curl -X POST http://localhost:3017/think \
    -H "Content-Type: application/json" \
    -d '{"problem": "Why is the sky blue?"}'
```

## Troubleshooting

```bash
ollama pull lfm2.5-thinking
```

## See Also

- [Ollama](https://github.com/ollama/ollama)
