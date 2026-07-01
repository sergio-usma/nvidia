# CodeQwen Node.js API Server

A production-ready REST API server for code generation, analysis, and refactoring using CodeQwen and other coding models via Ollama. This server provides a unified interface for multiple code-related AI operations.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Server Implementation](#server-implementation)
7. [API Endpoints](#api-endpoints)
8. [Usage Examples](#usage-examples)
9. [Client Libraries](#client-libraries)
10. [Error Handling](#error-handling)
11. [Security Considerations](#security-considerations)
12. [Performance Tuning](#performance-tuning)
13. [Deployment](#deployment)
14. [Troubleshooting](#troubleshooting)

---

## Overview

This API server wraps Ollama's code generation models (CodeQwen, Qwen2.5-Coder, Qwen3-Coder, Granite) with a RESTful interface that provides:

- **Code Generation**: Create new code from natural language prompts
- **Code Explanation**: Understand what code does
- **Bug Fixing**: Identify and fix issues in code
- **Test Generation**: Create unit tests for existing code
- **Code Refactoring**: Improve code structure and readability
- **Interactive Chat**: Conversational coding assistance

### Why Use This Server?

| Feature | Benefit |
|---------|---------|
| Unified API | Single interface for multiple coding models |
| RESTful Design | Easy to integrate with any technology |
| Streaming Support | Real-time code generation feedback |
| Error Handling | Graceful degradation with meaningful errors |
| CORS Enabled | Works with web applications |
| Model Switching | Easy to switch between different models |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CodeQwen API Server                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │   Express   │───▶│   Ollama    │───▶│  CodeQwen   │        │
│  │   Server    │    │   Client    │    │   Model     │        │
│  └──────┬──────┘    └─────────────┘    └─────────────┘        │
│         │                                                      │
│  ┌──────┴──────┐                                               │
│  │  REST API   │                                               │
│  │  Endpoints  │                                               │
│  └─────────────┘                                               │
│                                                                 │
│  Endpoints:                                                    │
│  • POST /api/code     → Generate new code                      │
│  • POST /api/explain  → Explain existing code                  │
│  • POST /api/fix      → Fix bugs in code                       │
│  • POST /api/test     → Generate unit tests                    │
│  • POST /api/refactor → Refactor code                          │
│  • POST /api/chat     → Conversational assistance              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Request/Response Flow

```
Client Request
      │
      ▼
┌─────────────────┐
│  Express Server │ ◀── Validates request
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Build Prompt   │ ◀── Formats for Ollama
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Ollama Client  │ ◀── Calls local Ollama
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  CodeQwen Model │ ◀── Generates response
└────────┬────────┘
         │
         ▼
    JSON Response
```

---

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Node.js | 18+ | JavaScript runtime |
| npm | 9+ | Package manager |
| Ollama | Latest | Local LLM server |
| codeqwen | Latest | Code generation model |

### System Requirements

- **Minimum**: 4GB RAM (for smaller models)
- **Recommended**: 16GB+ RAM (for CodeQwen full performance)
- **Storage**: 500MB for model weights

### Pre-Installation Checklist

```bash
# 1. Verify Node.js is installed
node --version  # Should be v18.x or higher

# 2. Verify npm is installed
npm --version   # Should be v9.x or higher

# 3. Verify Ollama is installed and running
ollama --version
ollama list     # Should show installed models

# 4. Pull required model
ollama pull codeqwen

# 5. Test Ollama is responding
curl http://localhost:11434/api/tags
```

---

## Installation

### Step 1: Create Project Directory

```bash
# Create a new directory for the project
mkdir -p ~/code-server
cd ~/code-server
```

### Step 2: Initialize Node.js Project

```bash
# Create package.json with default settings
npm init -y

# This creates a basic package.json:
# {
#   "name": "code-server",
#   "version": "1.0.0",
#   "main": "index.js",
#   "scripts": {
#     "test": "echo \"Error: no test specified\" && exit 1"
#   },
#   "keywords": [],
#   "author": "",
#   "license": "ISC"
# }
```

### Step 3: Install Dependencies

```bash
# Install required packages
npm install express ollama cors body-parser

# Package explanations:
# • express     - Web framework for REST API
# • ollama     - Official Ollama JavaScript client
# • cors       - Cross-Origin Resource Sharing support
# • body-parser - Parse JSON request bodies
```

### Step 4: Verify Installation

```bash
# Check installed packages
npm list --depth=0

# Should show:
# ├── body-parser@1.x.x
# ├── cors@2.x.x
# ├── express@4.x.x
# └── ollama@0.x.x
```

---

## Configuration

### Environment Variables

Create a `.env` file for configuration:

```bash
# Server Configuration
PORT=3000
NODE_ENV=development

# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_TIMEOUT=120000  # 2 minutes in milliseconds

# Model Configuration
DEFAULT_MODEL=codeqwen

# CORS Configuration (comma-separated list)
CORS_ORIGIN=*

# Logging
LOG_LEVEL=info
```

### Model Configuration

The server supports multiple coding models. Modify the `MODELS` object in `server.js`:

```javascript
const MODELS = {
    // Model alias: Ollama model name
    'codeqwen': 'codeqwen',           // Default code generation
    'qwen2.5': 'qwen2.5-coder',        // Qwen 2.5 Coder
    'qwen3': 'qwen3-coder',            // Qwen 3 Coder (latest)
    'granite': 'granite3.3',           // IBM Granite
    'deepseek': 'deepseek-coder'      // DeepSeek Coder
};
```

### Model Selection Guide

| Model | Best For | Speed | Quality |
|-------|----------|-------|---------|
| codeqwen | General coding | Medium | Good |
| qwen2.5 | Python/JavaScript | Fast | Very Good |
| qwen3 | Complex reasoning | Medium | Excellent |
| granite | Enterprise Java | Medium | Good |

---

## Server Implementation

Create `server.js` with comprehensive error handling and logging:

```javascript
// ============================================================================
// CodeQwen API Server
// A RESTful API for code generation, analysis, and refactoring
// ============================================================================

// ----------------------------------------------------------------------------
// Module Imports
// ----------------------------------------------------------------------------
const express = require('express');
const { Ollama } = require('ollama');
const cors = require('cors');
const bodyParser = require('body-parser');

// ----------------------------------------------------------------------------
// Configuration
// ----------------------------------------------------------------------------
const CONFIG = {
    port: process.env.PORT || 3000,
    ollamaHost: process.env.OLLAMA_HOST || 'http://localhost:11434',
    defaultModel: process.env.DEFAULT_MODEL || 'codeqwen',
    corsOrigin: process.env.CORS_ORIGIN || '*',
    requestTimeout: parseInt(process.env.OLLAMA_TIMEOUT) || 120000
};

// Model mappings - maps friendly names to actual Ollama model names
const MODELS = {
    'codeqwen': 'codeqwen',
    'qwen2.5': 'qwen2.5-coder',
    'qwen3': 'qwen3-coder',
    'granite': 'granite3.3'
};

// ----------------------------------------------------------------------------
// Initialize Express App
// ----------------------------------------------------------------------------
const app = express();

// Middleware configuration
app.use(cors({
    origin: CONFIG.corsOrigin  // Allow requests from any origin
}));
app.use(bodyParser.json({ limit: '10mb' }));  // Parse JSON bodies, allow 10MB payloads
app.use(express.static('public'));  // Serve static files if needed

// Request logging middleware
app.use((req, res, next) => {
    const start = Date.now();
    res.on('finish', () => {
        const duration = Date.now() - start;
        console.log(`${req.method} ${req.path} ${res.statusCode} ${duration}ms`);
    });
    next();
});

// ----------------------------------------------------------------------------
// Ollama Client Initialization
// ----------------------------------------------------------------------------
const ollama = new Ollama({ host: CONFIG.ollamaHost });

// ----------------------------------------------------------------------------
// Helper Functions
// ----------------------------------------------------------------------------

/**
 * Get the actual model name from alias
 * @param {string} modelAlias - The alias (e.g., 'codeqwen', 'qwen2.5')
 * @returns {string} - The actual model name
 */
function getModelName(modelAlias) {
    return MODELS[modelAlias] || MODELS[CONFIG.defaultModel];
}

/**
 * Build a standardized response
 * @param {boolean} success - Whether the operation succeeded
 * @param {*} data - The response data
 * @param {string} error - Error message if failed
 * @returns {object} - Standardized response object
 */
function buildResponse(success, data, error = null) {
    const response = { success };
    if (success) {
        response.data = data;
        response.timestamp = new Date().toISOString();
    } else {
        response.error = error;
        response.timestamp = new Date().toISOString();
    }
    return response;
}

// ----------------------------------------------------------------------------
// API Routes
// ----------------------------------------------------------------------------

// ----------------------------------------------------------------------------
// Health Check Endpoint
// Purpose: Verify the server is running and Ollama is accessible
// ----------------------------------------------------------------------------
app.get('/health', async (req, res) => {
    try {
        // Test Ollama connectivity
        const tags = await ollama.list();
        res.json(buildResponse(true, {
            status: 'ok',
            server: 'CodeQwen API',
            version: '1.0.0',
            ollamaConnected: true,
            models: tags.models.map(m => m.name),
            timestamp: new Date().toISOString()
        }));
    } catch (error) {
        res.status(503).json(buildResponse(false, null, `Ollama not accessible: ${error.message}`));
    }
});

// ----------------------------------------------------------------------------
// List Available Models
// Purpose: Show which models are available for use
// ----------------------------------------------------------------------------
app.get('/models', (req, res) => {
    res.json(buildResponse(true, {
        available: Object.keys(MODELS),
        mappings: MODELS,
        default: CONFIG.defaultModel
    }));
});

// ----------------------------------------------------------------------------
// Code Generation Endpoint
// Purpose: Generate new code from a natural language prompt
// ----------------------------------------------------------------------------
app.post('/api/code', async (req, res) => {
    try {
        // Extract and validate request parameters
        const { 
            prompt,           // Required: What to generate
            language = 'python',  // Default language
            model = CONFIG.defaultModel,  // Model selection
            temperature = 0.3,  // Creativity level (0-2)
            maxTokens = 2048    // Maximum response length
        } = req.body;

        // Validate required fields
        if (!prompt) {
            return res.status(400).json(
                buildResponse(false, null, 'Prompt is required')
            );
        }

        // Build the prompt with clear instructions
        const fullPrompt = `You are an expert ${language} programmer. 
Generate clean, well-documented ${language} code for the following request:

REQUEST: ${prompt}

Requirements:
- Write complete, working code
- Include comments where helpful
- Follow best practices
- Return ONLY the code, no explanations outside the code comments.`;

        // Call Ollama to generate code
        const response = await ollama.generate({
            model: getModelName(model),
            prompt: fullPrompt,
            options: {
                temperature,
                num_predict: maxTokens,
                stop: ['```']  // Stop at code blocks
            }
        });

        // Return successful response
        res.json(buildResponse(true, {
            code: response.response,
            model: getModelName(model),
            language,
            prompt,
            tokensGenerated: response.eval_count
        }));

    } catch (error) {
        console.error('Code generation error:', error);
        res.status(500).json(buildResponse(false, null, error.message));
    }
});

// ----------------------------------------------------------------------------
// Code Explanation Endpoint
// Purpose: Explain what a piece of code does
// ----------------------------------------------------------------------------
app.post('/api/explain', async (req, res) => {
    try {
        const { 
            code,           // Required: Code to explain
            model = CONFIG.defaultModel,
            detailLevel = 'comprehensive'  // 'brief', 'comprehensive', 'technical'
        } = req.body;

        if (!code) {
            return res.status(400).json(
                buildResponse(false, null, 'Code is required')
            );
        }

        // Adjust prompt based on detail level
        const detailInstructions = {
            brief: 'Provide a brief 2-3 sentence explanation.',
            comprehensive: 'Explain what the code does, how it works, and any important details.',
            technical: 'Provide a detailed technical explanation including time/space complexity if applicable.'
        };

        const response = await ollama.generate({
            model: getModelName(model),
            prompt: `Explain this code:\n\n${code}\n\n${detailInstructions[detailLevel]}`,
            options: { 
                temperature: 0.5, 
                num_predict: 512 
            }
        });

        res.json(buildResponse(true, {
            explanation: response.response,
            code,
            detailLevel
        }));

    } catch (error) {
        console.error('Explain error:', error);
        res.status(500).json(buildResponse(false, null, error.message));
    }
});

// ----------------------------------------------------------------------------
// Bug Fixing Endpoint
// Purpose: Find and fix bugs in code
// ----------------------------------------------------------------------------
app.post('/api/fix', async (req, res) => {
    try {
        const { 
            code,           // Required: Code with bugs
            model = CONFIG.defaultModel,
            fixLevel = 'safe'  // 'safe' (minimal) or 'aggressive' (refactor)
        } = req.body;

        if (!code) {
            return res.status(400).json(
                buildResponse(false, null, 'Code is required')
            );
        }

        const fixPrompt = fixLevel === 'aggressive' 
            ? `Analyze and fix bugs in this code. Also improve code quality:\n\n${code}\n\nReturn the corrected and improved code.`
            : `Find and fix bugs in this code. Make minimal changes:\n\n${code}\n\nReturn the corrected code only.`;

        const response = await ollama.generate({
            model: getModelName(model),
            prompt: fixPrompt,
            options: { 
                temperature: 0.2,  // Low temperature for focused fixes
                num_predict: 2048 
            }
        });

        res.json(buildResponse(true, {
            fixed: response.response,
            original: code,
            fixLevel
        }));

    } catch (error) {
        console.error('Fix error:', error);
        res.status(500).json(buildResponse(false, null, error.message));
    }
});

// ----------------------------------------------------------------------------
// Test Generation Endpoint
// Purpose: Generate unit tests for existing code
// ----------------------------------------------------------------------------
app.post('/api/test', async (req, res) => {
    try {
        const { 
            code,               // Required: Code to test
            framework = 'pytest', // Testing framework
            model = CONFIG.defaultModel,
            testType = 'unit'    // 'unit', 'integration', 'e2e'
        } = req.body;

        if (!code) {
            return res.status(400).json(
                buildResponse(false, null, 'Code is required')
            );
        }

        // Framework mappings
        const frameworkMapping = {
            'pytest': 'Python pytest',
            'jest': 'JavaScript Jest',
            'unittest': 'Python unittest',
            'mocha': 'JavaScript Mocha',
            'junit': 'Java JUnit',
            'go': 'Go testing package',
            'rspec': 'Ruby RSpec'
        };

        const frameworkName = frameworkMapping[framework] || framework;

        const response = await ollama.generate({
            model: getModelName(model),
            prompt: `Generate ${testType} tests using ${frameworkName} for:\n\n${code}\n\nInclude setup, teardown, and multiple test cases.`,
            options: { 
                temperature: 0.3, 
                num_predict: 1024 
            }
        });

        res.json(buildResponse(true, {
            tests: response.response,
            framework,
            testType,
            code
        }));

    } catch (error) {
        console.error('Test generation error:', error);
        res.status(500).json(buildResponse(false, null, error.message));
    }
});

// ----------------------------------------------------------------------------
// Code Refactoring Endpoint
// Purpose: Improve code structure and readability
// ----------------------------------------------------------------------------
app.post('/api/refactor', async (req, res) => {
    try {
        const { 
            code,           // Required: Code to refactor
            style = 'clean', // Refactoring style
            model = CONFIG.defaultModel
        } = req.body;

        if (!code) {
            return res.status(400).json(
                buildResponse(false, null, 'Code is required')
            );
        }

        // Style options
        const styleGuide = {
            'clean': 'Apply clean code principles: clear names, small functions, no duplication',
            'functional': 'Convert to functional programming style',
            'oop': 'Apply object-oriented design patterns',
            'performance': 'Optimize for performance',
            'readability': 'Maximize readability for maintenance'
        };

        const response = await ollama.generate({
            model: getModelName(model),
            prompt: `Refactor this code with ${style} style:\n\n${code}\n\n${styleGuide[style] || style}\n\nReturn the refactored code.`,
            options: { 
                temperature: 0.4, 
                num_predict: 2048 
            }
        });

        res.json(buildResponse(true, {
            refactored: response.response,
            original: code,
            style
        }));

    } catch (error) {
        console.error('Refactor error:', error);
        res.status(500).json(buildResponse(false, null, error.message));
    }
});

// ----------------------------------------------------------------------------
// Chat Endpoint
// Purpose: Conversational coding assistance
// ----------------------------------------------------------------------------
app.post('/api/chat', async (req, res) => {
    try {
        const { 
            messages,       // Required: Array of message objects
            model = CONFIG.defaultModel,
            temperature = 0.7,
            maxTokens = 1024
        } = req.body;

        // Validate messages array
        if (!messages || !Array.isArray(messages)) {
            return res.status(400).json(
                buildResponse(false, null, 'Messages array is required')
            );
        }

        // System prompt to set context
        const systemPrompt = `You are an expert programmer specializing in code generation, 
debugging, and best practices. You provide clear, accurate, and helpful responses.`;

        // Build chat history with system message
        const chatHistory = [
            { role: 'system', content: systemPrompt },
            ...messages
        ];

        const response = await ollama.chat({
            model: getModelName(model),
            messages: chatHistory,
            options: { 
                temperature, 
                num_predict: maxTokens 
            }
        });

        res.json(buildResponse(true, {
            response: response.message.content,
            model: getModelName(model),
            messageCount: messages.length
        }));

    } catch (error) {
        console.error('Chat error:', error);
        res.status(500).json(buildResponse(false, null, error.message));
    }
});

// ----------------------------------------------------------------------------
// Server Startup
// ----------------------------------------------------------------------------
app.listen(CONFIG.port, () => {
    console.log('='.repeat(60));
    console.log('CodeQwen API Server Started');
    console.log('='.repeat(60));
    console.log(`Server URL: http://localhost:${CONFIG.port}`);
    console.log(`Ollama Host: ${CONFIG.ollamaHost}`);
    console.log(`Default Model: ${CONFIG.defaultModel}`);
    console.log('='.repeat(60));
    console.log('Available Endpoints:');
    console.log('  GET  /health              - Server health check');
    console.log('  GET  /models              - List available models');
    console.log('  POST /api/code            - Generate code');
    console.log('  POST /api/explain         - Explain code');
    console.log('  POST /api/fix             - Fix bugs');
    console.log('  POST /api/test            - Generate tests');
    console.log('  POST /api/refactor        - Refactor code');
    console.log('  POST /api/chat            - Chat about code');
    console.log('='.repeat(60));
});
```

---

## API Endpoints

### Detailed Endpoint Documentation

#### 1. Health Check

```
GET /health
```

Returns server status and Ollama connectivity.

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "ok",
    "server": "CodeQwen API",
    "version": "1.0.0",
    "ollamaConnected": true,
    "models": ["codeqwen", "qwen2.5-coder"]
  }
}
```

#### 2. List Models

```
GET /models
```

Returns available models and their mappings.

#### 3. Generate Code

```
POST /api/code
Content-Type: application/json
```

**Request Body:**
```json
{
  "prompt": "function to sort array",
  "language": "javascript",
  "model": "codeqwen",
  "temperature": 0.3,
  "maxTokens": 2048
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "code": "function bubbleSort(arr) {\n  // ...\n}",
    "model": "codeqwen",
    "language": "javascript",
    "tokensGenerated": 128
  }
}
```

#### 4. Explain Code

```
POST /api/explain
Content-Type: application/json
```

**Request Body:**
```json
{
  "code": "function fib(n) { return n <= 1 ? n : fib(n-1) + fib(n-2); }",
  "detailLevel": "comprehensive"
}
```

#### 5. Fix Bugs

```
POST /api/fix
Content-Type: application/json
```

**Request Body:**
```json
{
  "code": "function add(a,b) return a + b",
  "fixLevel": "safe"
}
```

#### 6. Generate Tests

```
POST /api/test
Content-Type: application/json
```

**Request Body:**
```json
{
  "code": "function add(a, b) { return a + b; }",
  "framework": "jest",
  "testType": "unit"
}
```

#### 7. Refactor Code

```
POST /api/refactor
Content-Type: application/json
```

**Request Body:**
```json
{
  "code": "function x(a,b){return a+b}",
  "style": "clean"
}
```

#### 8. Chat

```
POST /api/chat
Content-Type: application/json
```

**Request Body:**
```json
{
  "messages": [
    {"role": "user", "content": "How do I center a div?"}
  ],
  "temperature": 0.7
}
```

---

## Usage Examples

### Using cURL

```bash
# Generate code
curl -X POST http://localhost:3000/api/code \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "function to calculate factorial",
    "language": "javascript"
  }'

# Explain code
curl -X POST http://localhost:3000/api/explain \
  -H "Content-Type: application/json" \
  -d '{
    "code": "const f = n => n <= 1 ? 1 : n * f(n-1);",
    "detailLevel": "comprehensive"
  }'

# Fix bugs
curl -X POST http://localhost:3000/api/fix \
  -H "Content-Type: application/json" \
  -d '{
    "code": "function add(a,b) return a + b"
  }'

# Generate tests
curl -X POST http://localhost:3000/api/test \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def fib(n): return n if n < 2 else fib(n-1) + fib(n-2)",
    "framework": "pytest"
  }'

# Refactor code
curl -X POST http://localhost:3000/api/refactor \
  -H "Content-Type: application/json" \
  -d '{
    "code": "function x(a,b){return a+b}",
    "style": "clean"
  }'
```

### Using JavaScript/TypeScript

```javascript
// Base configuration
const API_BASE = 'http://localhost:3000';

// Helper function for API calls
async function apiCall(endpoint, data) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    });
    return response.json();
}

// Generate code
async function generateCode(prompt, language = 'javascript') {
    const result = await apiCall('/api/code', { prompt, language });
    if (result.success) {
        console.log('Generated code:');
        console.log(result.data.code);
    } else {
        console.error('Error:', result.error);
    }
}

// Fix bugs
async function fixCode(buggyCode) {
    const result = await apiCall('/api/fix', { code: buggyCode });
    if (result.success) {
        console.log('Fixed code:');
        console.log(result.data.fixed);
    }
}

// Generate tests
async function generateTests(code, framework = 'jest') {
    const result = await apiCall('/api/test', { code, framework });
    if (result.success) {
        console.log('Generated tests:');
        console.log(result.data.tests);
    }
}

// Example usage
generateCode('React useEffect hook example', 'javascript');
```

### Using Python

```python
import requests

API_BASE = "http://localhost:3000"

def generate_code(prompt: str, language: str = "python") -> dict:
    """Generate code from prompt."""
    response = requests.post(
        f"{API_BASE}/api/code",
        json={"prompt": prompt, "language": language}
    )
    return response.json()

def explain_code(code: str, detail_level: str = "comprehensive") -> dict:
    """Explain what code does."""
    response = requests.post(
        f"{API_BASE}/api/explain",
        json={"code": code, "detailLevel": detail_level}
    )
    return response.json()

def fix_bugs(code: str) -> dict:
    """Fix bugs in code."""
    response = requests.post(
        f"{API_BASE}/api/fix",
        json={"code": code}
    )
    return response.json()

# Example usage
result = generate_code("function to reverse a string", "javascript")
print(result["data"]["code"])
```

---

## Error Handling

### Error Response Format

All errors follow this format:

```json
{
  "success": false,
  "error": "Error message description",
  "timestamp": "2024-01-15T10:30:00.000Z"
}
```

### HTTP Status Codes

| Status Code | Meaning | Common Causes |
|-------------|---------|---------------|
| 400 | Bad Request | Missing required fields, invalid JSON |
| 404 | Not Found | Invalid endpoint |
| 500 | Server Error | Ollama not running, model not found |
| 503 | Service Unavailable | Ollama not accessible |

### Common Errors and Solutions

| Error | Solution |
|-------|----------|
| `Ollama not accessible` | Start Ollama: `ollama serve` |
| `Model not found` | Pull model: `ollama pull codeqwen` |
| `Request timeout` | Increase timeout in config |
| `Memory exhausted` | Use smaller model or close other apps |

---

## Security Considerations

### For Production Deployment

1. **Enable Authentication**
```javascript
// Add API key middleware
const API_KEY = process.env.API_KEY;

function requireAuth(req, res, next) {
    const key = req.headers['x-api-key'];
    if (!key || key !== API_KEY) {
        return res.status(401).json(buildResponse(false, null, 'Unauthorized'));
    }
    next();
}

// Apply to routes
app.post('/api/*', requireAuth);
```

2. **Restrict CORS**
```javascript
// Only allow specific origins
app.use(cors({
    origin: ['https://yourdomain.com']
}));
```

3. **Limit Request Size**
```javascript
// Prevent large payloads
app.use(bodyParser.json({ limit: '1mb' }));
```

4. **Rate Limiting**
```javascript
// Add rate limiting
const rateLimit = require('express-rate-limit');
const limiter = rateLimit({
    windowMs: 15 * 60 * 1000, // 15 minutes
    max: 100 // limit each IP to 100 requests per window
});
app.use(limiter);
```

5. **Use HTTPS**
```bash
# Generate SSL certificate
openssl req -nodes -new -x509 -keyout server.key -out server.cert

# Run with HTTPS
const https = require('https');
const fs = require('fs');
https.createServer({
    key: fs.readFileSync('server.key'),
    cert: fs.readFileSync('server.cert')
}, app).listen(CONFIG.port);
```

---

## Performance Tuning

### Server Configuration

```javascript
// For better performance, adjust these:

// 1. Increase worker threads
// Use cluster module for multi-core

// 2. Enable response compression
const compression = require('compression');
app.use(compression());

// 3. Cache model list
let modelCache = null;
app.get('/models', async (req, res) => {
    if (modelCache && Date.now() - modelCache.timestamp < 60000) {
        return res.json(modelCache.data);
    }
    // ... fetch and cache
});
```

### Ollama Configuration

```bash
# In /etc/ollama.env or ~/.ollama.env:

# Use all available GPU layers
GPU_LAYERS=999

# Set context window
CONTEXT_LENGTH=8192

# Enable flash attention (faster)
FLASH_ATTENTION=1
```

### Model Selection for Performance

| Model | Speed | Memory | Best Use Case |
|-------|-------|--------|---------------|
| codeqwen | Medium | 4GB | General |
| qwen2.5-coder | Fast | 3GB | Quick tasks |
| qwen3-coder | Medium | 7GB | Complex logic |

---

## Deployment

### Using PM2 (Production Process Manager)

```bash
# Install PM2 globally
sudo npm install -g pm2

# Create ecosystem file
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'codeqwen-api',
    script: './server.js',
    instances: 'max',
    exec_mode: 'cluster',
    env: {
      NODE_ENV: 'production',
      PORT: 3000
    }
  }]
};
EOF

# Start the application
pm2 start ecosystem.config.js

# Enable auto-start on boot
pm2 startup
pm2 save
```

### Using Docker

```dockerfile
# Dockerfile
FROM node:18-slim

WORKDIR /app
COPY package*.json ./
RUN npm install --production

COPY server.js ./

EXPOSE 3000
CMD ["node", "server.js"]
```

```bash
# Build and run
docker build -t codeqwen-api .
docker run -d -p 3000:3000 --network host codeqwen-api
```

### Using Systemd

```ini
# /etc/systemd/system/codeqwen-api.service
[Unit]
Description=CodeQwen API Server
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/code-server
ExecStart=/usr/bin/node server.js
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable codeqwen-api
sudo systemctl start codeqwen-api
```

---

## Troubleshooting

### Server Won't Start

```bash
# Check if port is in use
lsof -i :3000

# Check Node.js version
node --version

# Verify dependencies
npm list
```

### Ollama Connection Issues

```bash
# Verify Ollama is running
ollama list

# Test Ollama API directly
curl http://localhost:11434/api/tags

# Restart Ollama
pkill ollama
ollama serve
```

### Model Not Found

```bash
# Pull the required model
ollama pull codeqwen
ollama pull qwen2.5-coder

# Verify models are downloaded
ollama list
```

### Slow Responses

```bash
# Check system resources
htop
jtop

# Optimize Ollama settings
export GPU_LAYERS=999
export CONTEXT_LENGTH=4096

# Use smaller models for faster responses
```

### Memory Issues

```bash
# Check available memory
free -h

# Close other applications
pkill -f chrome
pkill -f electron

# Use smaller model
# Change defaultModel in server.js to 'qwen2.5-coder'
```

---

## Related Documentation

- [Ollama Documentation](https://github.com/ollama/ollama)
- [Express.js Guide](https://expressjs.com/)
- [CodeQwen Model](https://ollama.com/library/codeqwen)
- [Qwen2.5-Coder](https://ollama.com/library/qwen2.5-coder)

---

## License

MIT License - See LICENSE file for details
