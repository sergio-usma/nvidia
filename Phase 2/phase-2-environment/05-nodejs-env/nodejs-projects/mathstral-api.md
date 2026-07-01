# MathStral Node.js API

A REST API for math problem solving using MathStral.

## Prerequisites

- [x] Ollama with `mathstral` model
- [x] Node.js 18+

## Installation

```bash
mkdir math-api
cd math-api
npm init -y
npm install express ollama cors body-parser mathjs
```

## Create the Server

Create `server.js`:

```javascript
const express = require('express');
const { Ollama } = require('ollama');
const cors = require('cors');
const bodyParser = require('body-parser');
const math = require('mathjs');

const app = express();
const ollama = new Ollama({ host: 'http://localhost:11434' });

app.use(cors());
app.use(bodyParser.json());

// Health
app.get('/health', (req, res) => {
    res.json({ status: 'ok', model: 'mathstral' });
});

// Evaluate expression
app.post('/api/evaluate', (req, res) => {
    try {
        const { expression } = req.body;
        
        if (!expression) {
            return res.status(400).json({ error: 'Expression required' });
        }
        
        const result = math.evaluate(expression);
        
        res.json({ expression, result: String(result) });
        
    } catch (error) {
        res.status(400).json({ error: error.message });
    }
});

// Solve derivative
app.post('/api/derivative', async (req, res) => {
    try {
        const { expression, variable = 'x' } = req.body;
        
        if (!expression) {
            return res.status(400).json({ error: 'Expression required' });
        }
        
        const deriv = math.derivative(expression, variable).toString();
        
        // Get explanation from LLM
        const explanation = await ollama.generate({
            model: 'mathstral',
            prompt: `Explain how to find the derivative of f(x) = ${expression}. The result is ${deriv}.`,
            options: { temperature: 0.5, num_predict: 256 }
        });
        
        res.json({
            expression,
            derivative: deriv,
            explanation: explanation.response
        });
        
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Solve integral (basic)
app.post('/api/integrate', async (req, res) => {
    try {
        const { expression, variable = 'x' } = req.body;
        
        if (!expression) {
            return res.status(400).json({ error: 'Expression required' });
        }
        
        // Use symbolic integration via LLM
        const response = await ollama.generate({
            model: 'mathstral',
            prompt: `Calculate the indefinite integral of ${expression} with respect to ${variable}. Provide the result with + C.`,
            options: { temperature: 0.3, num_predict: 256 }
        });
        
        res.json({
            expression,
            integral: response.response
        });
        
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Solve equation
app.post('/api/solve', async (req, res) => {
    try {
        const { equation, variable = 'x' } = req.body;
        
        if (!equation) {
            return res.status(400).json({ error: 'Equation required' });
        }
        
        // Parse equation like "x^2 + 2*x - 3 = 0"
        const [left, right] = equation.split('=').map(s => s.trim());
        const expr = left + '-(' + right + ')';
        
        const solutions = math.parse(expr).solve(variable);
        
        res.json({
            equation,
            solutions: solutions.map(s => s.toString())
        });
        
    } catch (error) {
        // Fallback to LLM
        try {
            const { equation, variable = 'x' } = req.body;
            const response = await ollama.generate({
                model: 'mathstral',
                prompt: `Solve for ${variable}: ${equation}. Provide step by step.`,
                options: { temperature: 0.3, num_predict: 512 }
            });
            
            res.json({ equation, solution: response.response });
            
        } catch (err) {
            res.status(400).json({ error: err.message });
        }
    }
});

// Math LLM Chat
app.post('/api/chat', async (req, res) => {
    try {
        const { message, topic } = req.body;
        
        if (!message) {
            return res.status(400).json({ error: 'Message required' });
        }
        
        const prompt = topic 
            ? `You are a math tutor. Help with: ${message}`
            : `Solve this math problem step by step: ${message}`;
        
        const response = await ollama.generate({
            model: 'mathstral',
            prompt,
            options: { temperature: 0.5, num_predict: 1024 }
        });
        
        res.json({
            question: message,
            answer: response.response
        });
        
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Generate practice problems
app.post('/api/practice', async (req, res) => {
    try {
        const { topic = 'algebra', difficulty = 'medium' } = req.body;
        
        const response = await ollama.generate({
            model: 'mathstral',
            prompt: `Generate 5 ${difficulty} ${topic} practice problems with solutions.`,
            options: { temperature: 0.7, num_predict: 512 }
        });
        
        res.json({
            topic,
            difficulty,
            problems: response.response
        });
        
    } catch (error) {
        res.status(500).json({ error: error.message });
    }
});

// Simplify expression
app.post('/api/simplify', (req, res) => {
    try {
        const { expression } = req.body;
        
        if (!expression) {
            return res.status(400).json({ error: 'Expression required' });
        }
        
        const simplified = math.simplify(expression).toString();
        
        res.json({ expression, simplified });
        
    } catch (error) {
        res.status(400).json({ error: error.message });
    }
});

// Matrix operations
app.post('/api/matrix', (req, res) => {
    try {
        const { operation, matrix1, matrix2 } = req.body;
        
        const m1 = matrix1;
        const m2 = matrix2;
        
        let result;
        
        switch (operation) {
            case 'add':
                result = math.add(m1, m2);
                break;
            case 'multiply':
                result = math.multiply(m1, m2);
                break;
            case 'determinant':
                result = math.det(m1);
                break;
            case 'inverse':
                result = math.inv(m1);
                break;
            case 'transpose':
                result = math.transpose(m1);
                break;
            default:
                return res.status(400).json({ error: 'Invalid operation' });
        }
        
        res.json({ operation, result: result.toString() });
        
    } catch (error) {
        res.status(400).json({ error: error.message });
    }
});

const PORT = process.env.PORT || 3002;
app.listen(PORT, () => {
    console.log(`MathStral API running on port ${PORT}`);
});
```

## Run

```bash
node server.js
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/evaluate` | POST | Evaluate expression |
| `/api/derivative` | POST | Calculate derivative |
| `/api/integrate` | POST | Calculate integral |
| `/api/solve` | POST | Solve equation |
| `/api/chat` | POST | Math chat |
| `/api/practice` | POST | Generate problems |
| `/api/simplify` | POST | Simplify expression |
| `/api/matrix` | POST | Matrix operations |

## Example Usage

```bash
# Evaluate
curl -X POST http://localhost:3002/api/evaluate \
  -H "Content-Type: application/json" \
  -d '{"expression": "2^10 + 5*3"}'

# Derivative
curl -X POST http://localhost:3002/api/derivative \
  -H "Content-Type: application/json" \
  -d '{"expression": "x^2 + 3*x + 1"}'

# Chat
curl -X POST http://localhost:3002/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain the chain rule in derivatives"}'
```
