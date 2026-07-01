# DeepSeek R1 Node.js Reasoning API

REST API using deepseek-r1:8b for chain-of-thought reasoning.

## Setup

```bash
mkdir deepseek-api
cd deepseek-api
npm init -y
npm install express ollama cors body-parser
```

## server.js

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const cors = require('cors');

const app = express();
const ollama = new Ollama({ host: 'http://localhost:11434' });

app.use(cors());
app.use(express.json());

// Chain of thought
app.post('/api/reason', async (req, res) => {
    try {
        const { problem, show_steps = true } = req.body;
        
        const prompt = show_steps 
            ? `Solve step by step: ${problem}`
            : `Solve: ${problem}`;
        
        const response = await ollama.generate({
            model: 'deepseek-r1:8b',
            prompt,
            options: { temperature: 0.5, num_predict: 2048 }
        });
        
        res.json({ problem, solution: response.response });
        
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Analyze logic
app.post('/api/analyze', async (req, res) => {
    try {
        const { statement } = req.body;
        
        const response = await ollama.generate({
            model: 'deepseek-r1:8b',
            prompt: `Analyze logically: ${statement}`,
            options: { temperature: 0.3, num_predict: 1024 }
        });
        
        res.json({ statement, analysis: response.response });
        
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Compare solutions
app.post('/api/compare', async (req, res) => {
    try {
        const { problem, solutions } = req.body;
        
        let prompt = `Compare solutions for: ${problem}\n\n`;
        solutions.forEach((s, i) => prompt += `${i+1}. ${s}\n`);
        
        const response = await ollama.generate({
            model: 'deepseek-r1:8b',
            prompt,
            options: { temperature: 0.3, num_predict: 512 }
        });
        
        res.json({ comparison: response.response });
        
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

app.listen(3003, () => console.log('DeepSeek R1 API on port 3003'));
```

## Run

```bash
node server.js
```

## Usage

```bash
curl -X POST http://localhost:3003/api/reason \
  -H "Content-Type: application/json" \
  -d '{"problem": "If all roses are flowers and some flowers fade quickly, what can we conclude about roses?"}'
```
