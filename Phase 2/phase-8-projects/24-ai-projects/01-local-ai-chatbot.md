# Project 1: Local AI Chatbot with Web Interface

A comprehensive guide to building a production-ready AI chatbot web interface using Ollama and Flask. This project serves as the foundation for many other AI applications and demonstrates core concepts of building LLM-powered web applications.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Prerequisites](#prerequisites)
4. [What You'll Build](#what-youll-build)
5. [Project Structure](#project-structure)
6. [Step-by-Step Implementation](#step-by-step-implementation)
   - [Step 1: Create Project Directory](#step-1-create-project-directory)
   - [Step 2: Set Up Virtual Environment](#step-2-set-up-virtual-environment)
   - [Step 3: Create the Flask Chat Application](#step-3-create-the-flask-chat-application)
   - [Step 4: Create the Web Interface](#step-4-create-the-web-interface)
   - [Step 5: Create CSS Styles](#step-5-create-css-styles)
   - [Step 6: Create JavaScript Client](#step-6-create-javascript-client)
7. [Running the Application](#running-the-application)
8. [Testing the Chatbot](#testing-the-chatbot)
9. [Features Explained](#features-explained)
10. [Security Considerations](#security-considerations)
11. [Production Deployment](#production-deployment)
12. [Troubleshooting](#troubleshooting)
13. [Next Steps](#next-steps)

---

## Overview

This project creates a fully functional web-based chatbot with:

- **Real-time Streaming**: Watch responses appear as they're generated
- **Multi-Model Support**: Switch between any Ollama model
- **Chat History**: Persistent conversations during session
- **Modern UI**: Clean, responsive interface
- **RESTful API**: Programmatic access to chat functionality

### Why Build This?

This chatbot serves as the foundation for more complex projects:

| Use Case | How This Helps |
|----------|----------------|
| Voice Assistant | Add voice input/output on top |
| RAG System | Connect to knowledge base |
| Code Assistant | Integrate with coding models |
| Multi-modal | Add image upload support |
| Agents | Build autonomous agents |

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Local AI Chatbot Architecture                        │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   ┌─────────────┐      ┌─────────────┐      ┌─────────────┐              │
│   │   Browser   │─────▶│   Flask     │─────▶│   Ollama   │              │
│   │   (HTML/JS) │◀─────│   Server    │◀─────│   (LLM)    │              │
│   └─────────────┘      └─────────────┘      └─────────────┘              │
│        │                    │                    │                         │
│        │                    │                    │                         │
│   ┌────▼────┐         ┌─────▼─────┐       ┌─────▼─────┐               │
│   │  HTML   │         │  Python   │       │  llama3.2 │               │
│   │  CSS    │         │  Requests │       │  (Model)  │               │
│   │  JS     │         │  JSON     │       │           │               │
│   └─────────┘         └───────────┘       └───────────┘               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Request Flow

```
User Message
     │
     ▼
┌─────────────────┐
│  HTML Form/JS   │  User types message in browser
└────────┬────────┘
         │ POST /api/chat
         ▼
┌─────────────────┐
│  Flask Route    │  Receive JSON with messages
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Build Prompt   │  Format messages for Ollama
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Ollama API     │  Forward to local Ollama server
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Stream Response│  Yield tokens as they're generated
└────────┬────────┘
         │
         ▼
    Client Display
```

---

## Prerequisites

### Required Software

Before starting this project, ensure you have:

| Requirement | Verification Command | Notes |
|-------------|---------------------|-------|
| Ubuntu 22.04 | `lsb_release -a` | Should show 22.04 |
| Python 3.10+ | `python3 --version` | Check version |
| Ollama | `ollama --version` | Install if needed |
| pip | `pip3 --version` | Package manager |
| Git | `git --version` | For cloning |

### Pre-Installation Checklist

Run these commands to verify your environment:

```bash
# 1. Check Python version (should be 3.10+)
python3 --version

# 2. Verify pip is installed
pip3 --version

# 3. Check Ollama is installed
ollama --version

# 4. Verify Ollama is running
curl http://localhost:11434/api/tags

# 5. Pull a model for testing
ollama pull llama3.2

# 6. Test the model
ollama run llama3.2 "Hello"
```

### Required Knowledge

- Basic Python programming
- HTML/CSS/JavaScript fundamentals
- Understanding of REST APIs
- Command line basics

---

## What You'll Build

### Features

| Feature | Description |
|---------|-------------|
| Real-time Chat | Stream responses token-by-token |
| Model Selection | Dropdown to switch between models |
| Chat History | Messages persist during session |
| System Stats | Show token count and timing |
| Error Handling | Graceful error messages |
| Responsive Design | Works on desktop and mobile |

### Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Frontend | HTML5 + CSS3 | User interface |
| Frontend | Vanilla JavaScript | Interactivity |
| Backend | Flask | Web server |
| AI | Ollama | Local LLM inference |
| API | REST | Client-server communication |

---

## Project Structure

Create this directory structure:

```bash
~/ai-projects/chatbot/
├── app.py                    # Flask application (backend)
├── requirements.txt          # Python dependencies
├── config.py                 # Configuration settings
├── .env                      # Environment variables
├── templates/
│   └── index.html           # Main chat interface
├── static/
│   ├── style.css            # Styling
│   └── chat.js             # Client-side JavaScript
└── logs/                    # Application logs (created automatically)
```

---

## Step-by-Step Implementation

### Step 1: Create Project Directory

```bash
# Navigate to home directory
cd ~

# Create project directory
mkdir -p ai-projects/chatbot

# Navigate into it
cd ai-projects/chatbot

# Create subdirectories
mkdir -p templates static logs

# Verify structure
ls -la
```

### Step 2: Set Up Virtual Environment

```bash
# Use system site packages to access Jetson-optimized packages
python3 -m venv --system-site-packages venv

# Activate the virtual environment
source venv/bin/activate

# Verify activation (you should see (venv) in prompt)
which python

# Upgrade pip
pip install --upgrade pip

# Install Flask
pip install flask flask-cors python-dotenv requests

# Create requirements.txt for reproducibility
pip freeze > requirements.txt
```

### Step 3: Create the Flask Chat Application

Create `app.py`:

```python
#!/usr/bin/env python3
"""
Local AI Chatbot - Flask Backend

A production-ready Flask application that provides a RESTful API
for interacting with Ollama's local LLM models.

Author: Your Name
Version: 1.0.0
"""

# ============================================================================
# IMPORTS
# ============================================================================
import os
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
import requests
from dotenv import load_dotenv

# ============================================================================
# CONFIGURATION
# ============================================================================

# Load environment variables from .env file
load_dotenv()

# Flask app configuration
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JSON_SORT_KEYS'] = False

# Ollama configuration
OLLAMA_BASE = os.environ.get('OLLAMA_BASE', 'http://localhost:11434')
DEFAULT_MODEL = os.environ.get('DEFAULT_MODEL', 'llama3.2')
OLLAMA_TIMEOUT = int(os.environ.get('OLLAMA_TIMEOUT', '120'))

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/chatbot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_ollama_models():
    """
    Fetch available models from Ollama.
    
    Returns:
        list: List of available model names
    """
    try:
        response = requests.get(f"{OLLAMA_BASE}/api/tags", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return [model['name'] for model in data.get('models', [])]
        return []
    except Exception as e:
        logger.error(f"Error fetching models: {e}")
        return []


def format_messages(messages):
    """
    Convert message history to prompt format for Ollama.
    
    Args:
        messages (list): List of message dictionaries with 'role' and 'content'
    
    Returns:
        str: Formatted prompt string
    """
    prompt = ""
    for msg in messages:
        role = msg.get('role', 'user')
        content = msg.get('content', '')
        prompt += f"{role}: {content}\n"
    prompt += "assistant: "
    return prompt


# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """
    Main entry point - serves the chat interface.
    
    Returns:
        HTML: Rendered template
    """
    return render_template('index.html')


@app.route('/api/models', methods=['GET'])
def list_models():
    """
    Get list of available Ollama models.
    
    Returns:
        JSON: List of model names and details
    """
    try:
        models = get_ollama_models()
        return jsonify({
            'success': True,
            'models': models,
            'default': DEFAULT_MODEL
        })
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint - streams LLM responses.
    
    Expects JSON with:
        - model: Model name (optional, defaults to DEFAULT_MODEL)
        - messages: List of message objects
    
    Yields:
        Server-sent events with response tokens
    """
    try:
        data = request.get_json()
        
        # Validate request
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        model = data.get('model', DEFAULT_MODEL)
        messages = data.get('messages', [])
        
        # Add user message if not in messages
        user_message = data.get('message', '')
        if user_message and not any(m.get('role') == 'user' for m in messages):
            messages.append({'role': 'user', 'content': user_message})
        
        # Build prompt from messages
        prompt = format_messages(messages)
        
        logger.info(f"Chat request - Model: {model}, Messages: {len(messages)}")
        
        def generate():
            """Stream response from Ollama."""
            try:
                response = requests.post(
                    f"{OLLAMA_BASE}/api/generate",
                    json={
                        'model': model,
                        'prompt': prompt,
                        'stream': True,
                        'options': {
                            'temperature': 0.7,
                            'top_p': 0.9,
                            'repeat_penalty': 1.1
                        }
                    },
                    stream=True,
                    timeout=OLLAMA_TIMEOUT
                )
                
                # Stream each token
                for line in response.iter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            token = data.get('response', '')
                            if token:
                                yield f"data: {json.dumps({'token': token})}\n\n"
                        except json.JSONDecodeError:
                            continue
                
                # Send done signal
                yield f"data: {json.dumps({'done': True})}\n\n"
                
            except requests.exceptions.Timeout:
                yield f"data: {json.dumps({'error': 'Request timed out'})}\n\n"
            except Exception as e:
                logger.error(f"Generation error: {e}")
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chat/non-stream', methods=['POST'])
def chat_non_stream():
    """
    Non-streaming chat endpoint (alternative).
    
    Returns:
        JSON: Complete response
    """
    try:
        data = request.get_json()
        model = data.get('model', DEFAULT_MODEL)
        messages = data.get('messages', [])
        
        # Add user message if provided
        user_message = data.get('message', '')
        if user_message:
            messages.append({'role': 'user', 'content': user_message})
        
        prompt = format_messages(messages)
        
        response = requests.post(
            f"{OLLAMA_BASE}/api/generate",
            json={
                'model': model,
                'prompt': prompt,
                'stream': False
            },
            timeout=OLLAMA_TIMEOUT
        )
        
        if response.status_code == 200:
            result = response.json()
            return jsonify({
                'success': True,
                'response': result.get('response', ''),
                'model': model
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Ollama request failed'
            }), 500
            
    except Exception as e:
        logger.error(f"Non-stream chat error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint for monitoring.
    
    Returns:
        JSON: Server status
    """
    try:
        # Check Ollama connectivity
        ollama_status = 'connected'
        try:
            requests.get(f"{OLLAMA_BASE}/api/tags", timeout=5)
        except:
            ollama_status = 'disconnected'
        
        return jsonify({
            'status': 'healthy',
            'ollama': ollama_status,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal error: {error}")
    return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# MAIN
# ============================================================================

if __name__ == '__main__':
    # Ensure log directory exists
    os.makedirs('logs', exist_ok=True)
    
    # Run the Flask application
    logger.info("Starting AI Chatbot...")
    logger.info(f"Ollama URL: {OLLAMA_BASE}")
    logger.info(f"Default Model: {DEFAULT_MODEL}")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    )
```

### Step 4: Create Configuration File

Create `config.py`:

```python
"""
Configuration Settings

Centralized configuration for the chatbot application.
Load from environment or use sensible defaults.
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Config:
    """Base configuration."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key')
    DEBUG = False
    TESTING = False
    
    # Ollama settings
    OLLAMA_BASE = os.environ.get('OLLAMA_BASE', 'http://localhost:11434')
    DEFAULT_MODEL = os.environ.get('DEFAULT_MODEL', 'llama3.2')
    OLLAMA_TIMEOUT = int(os.environ.get('OLLAMA_TIMEOUT', '120'))
    
    # Chat settings
    MAX_MESSAGE_LENGTH = 10000
    MAX_HISTORY_MESSAGES = 50
    DEFAULT_TEMPERATURE = 0.7
    
    # Server settings
    HOST = '0.0.0.0'
    PORT = int(os.environ.get('PORT', '5000'))


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEFAULT_MODEL = 'llama3.2'


# Configuration dictionary for easy switching
config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config():
    """Get configuration based on environment."""
    env = os.environ.get('FLASK_ENV', 'development')
    return config_by_name.get(env, DevelopmentConfig)
```

### Step 5: Create Environment File

Create `.env`:

```bash
# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-change-in-production

# Ollama Configuration
OLLAMA_BASE=http://localhost:11434
DEFAULT_MODEL=llama3.2
OLLAMA_TIMEOUT=120

# Server Configuration
PORT=5000
```

### Step 6: Create the Web Interface

Create `templates/index.html`:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Local AI Chatbot</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <h1>🤖 Local AI Chatbot</h1>
            <div class="controls">
                <label for="model-select">Model:</label>
                <select id="model-select">
                    <option value="llama3.2">llama3.2</option>
                </select>
                <button id="clear-btn" class="btn-secondary">Clear Chat</button>
            </div>
        </header>

        <!-- Chat Messages -->
        <div id="chat-container" class="chat-container">
            <div class="message system">
                <div class="message-content">
                    <p>👋 Welcome! I'm your local AI assistant running on Ollama.</p>
                    <p>Select a model from the dropdown and start chatting!</p>
                </div>
            </div>
        </div>

        <!-- Input Area -->
        <div class="input-area">
            <form id="chat-form" class="chat-form">
                <textarea 
                    id="user-input" 
                    placeholder="Type your message..."
                    rows="3"
                    autofocus
                ></textarea>
                <button type="submit" id="send-btn" class="btn-primary">
                    Send
                </button>
            </form>
            <div class="status-bar">
                <span id="status">Ready</span>
                <span id="token-count"></span>
            </div>
        </div>
    </div>

    <script src="/static/chat.js"></script>
</body>
</html>
```

### Step 7: Create CSS Styles

Create `static/style.css`:

```css
/* ============================================================================
   CSS Styles for Local AI Chatbot
   ============================================================================ */

:root {
    /* Color scheme */
    --bg-primary: #1a1a2e;
    --bg-secondary: #16213e;
    --bg-tertiary: #0f3460;
    --text-primary: #e8e8e8;
    --text-secondary: #a0a0a0;
    --accent-primary: #e94560;
    --accent-secondary: #533483;
    --border-color: #2a2a4a;
    --success-color: #4ade80;
    --error-color: #f87171;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
    background-color: var(--bg-primary);
    color: var(--text-primary);
    line-height: 1.6;
}

.container {
    max-width: 900px;
    margin: 0 auto;
    height: 100vh;
    display: flex;
    flex-direction: column;
}

/* Header */
.header {
    padding: 1rem;
    background-color: var(--bg-secondary);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 1rem;
}

.header h1 {
    font-size: 1.5rem;
    color: var(--accent-primary);
}

.controls {
    display: flex;
    align-items: center;
    gap: 1rem;
}

select {
    padding: 0.5rem;
    border-radius: 4px;
    border: 1px solid var(--border-color);
    background-color: var(--bg-tertiary);
    color: var(--text-primary);
    font-size: 0.9rem;
}

/* Buttons */
.btn-primary, .btn-secondary {
    padding: 0.5rem 1rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: all 0.2s;
}

.btn-primary {
    background-color: var(--accent-primary);
    color: white;
}

.btn-primary:hover {
    background-color: #d13652;
}

.btn-primary:disabled {
    background-color: #666;
    cursor: not-allowed;
}

.btn-secondary {
    background-color: var(--bg-tertiary);
    color: var(--text-primary);
    border: 1px solid var(--border-color);
}

.btn-secondary:hover {
    background-color: var(--border-color);
}

/* Chat Container */
.chat-container {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

/* Messages */
.message {
    display: flex;
    flex-direction: column;
    max-width: 80%;
    animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

.message.user {
    align-self: flex-end;
}

.message.assistant {
    align-self: flex-start;
}

.message.system {
    align-self: center;
    text-align: center;
}

.message-content {
    padding: 0.75rem 1rem;
    border-radius: 12px;
    white-space: pre-wrap;
    word-wrap: break-word;
}

.message.user .message-content {
    background-color: var(--accent-primary);
    color: white;
    border-bottom-right-radius: 4px;
}

.message.assistant .message-content {
    background-color: var(--bg-secondary);
    border: 1px solid var(--border-color);
    border-bottom-left-radius: 4px;
}

.message.system .message-content {
    background-color: var(--bg-tertiary);
    color: var(--text-secondary);
    font-style: italic;
}

.message-meta {
    font-size: 0.75rem;
    color: var(--text-secondary);
    margin-top: 0.25rem;
    padding: 0 0.5rem;
}

/* Input Area */
.input-area {
    padding: 1rem;
    background-color: var(--bg-secondary);
    border-top: 1px solid var(--border-color);
}

.chat-form {
    display: flex;
    gap: 0.5rem;
    align-items: flex-end;
}

#user-input {
    flex: 1;
    padding: 0.75rem;
    border-radius: 8px;
    border: 1px solid var(--border-color);
    background-color: var(--bg-tertiary);
    color: var(--text-primary);
    font-family: inherit;
    font-size: 1rem;
    resize: none;
}

#user-input:focus {
    outline: none;
    border-color: var(--accent-primary);
}

#user-input::placeholder {
    color: var(--text-secondary);
}

/* Status Bar */
.status-bar {
    display: flex;
    justify-content: space-between;
    margin-top: 0.5rem;
    font-size: 0.8rem;
    color: var(--text-secondary);
}

#status {
    color: var(--success-color);
}

#status.error {
    color: var(--error-color);
}

/* Typing indicator */
.typing {
    display: inline-block;
    padding: 0.5rem 1rem;
    background-color: var(--bg-secondary);
    border-radius: 12px;
    border-bottom-left-radius: 4px;
}

.typing span {
    display: inline-block;
    width: 8px;
    height: 8px;
    background-color: var(--text-secondary);
    border-radius: 50%;
    margin: 0 2px;
    animation: typing 1.4s infinite;
}

.typing span:nth-child(2) { animation-delay: 0.2s; }
.typing span:nth-child(3) { animation-delay: 0.4s; }

@keyframes typing {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-5px); }
}

/* Responsive */
@media (max-width: 600px) {
    .header {
        flex-direction: column;
        align-items: flex-start;
    }
    
    .controls {
        width: 100%;
        justify-content: space-between;
    }
    
    .message {
        max-width: 95%;
    }
}
```

### Step 8: Create JavaScript Client

Create `static/chat.js`:

```javascript
/**
 * Chat Client JavaScript
 * Handles user interaction and API communication
 */

// ============================================================================
// CONFIGURATION
// ============================================================================

const API_BASE = '';  // Same origin
const DEFAULT_MODEL = 'llama3.2';

// ============================================================================
// STATE
// ============================================================================

let currentModel = DEFAULT_MODEL;
let messages = [];
let isStreaming = false;

// ============================================================================
// DOM ELEMENTS
// ============================================================================

const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('user-input');
const chatContainer = document.getElementById('chat-container');
const modelSelect = document.getElementById('model-select');
const sendBtn = document.getElementById('send-btn');
const clearBtn = document.getElementById('clear-btn');
const statusEl = document.getElementById('status');
const tokenCountEl = document.getElementById('token-count');

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    await loadModels();
    setupEventListeners();
});

async function loadModels() {
    try {
        const response = await fetch('/api/models');
        const data = await response.json();
        
        if (data.success && data.models.length > 0) {
            modelSelect.innerHTML = '';
            data.models.forEach(model => {
                const option = document.createElement('option');
                option.value = model;
                option.textContent = model;
                if (model === data.default) {
                    option.selected = true;
                }
                modelSelect.appendChild(option);
            });
        }
    } catch (error) {
        console.error('Error loading models:', error);
        showStatus('Error loading models', true);
    }
}

function setupEventListeners() {
    // Form submission
    chatForm.addEventListener('submit', handleSubmit);
    
    // Clear button
    clearBtn.addEventListener('click', clearChat);
    
    // Model selection
    modelSelect.addEventListener('change', (e) => {
        currentModel = e.target.value;
    });
    
    // Enter to send (Shift+Enter for newline)
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    });
}

// ============================================================================
// CHAT HANDLERS
// ============================================================================

async function handleSubmit(event) {
    event.preventDefault();
    
    const message = userInput.value.trim();
    if (!message || isStreaming) return;
    
    // Add user message
    addMessage('user', message);
    messages.push({ role: 'user', content: message });
    
    // Clear input
    userInput.value = '';
    
    // Show typing indicator
    showTypingIndicator();
    
    // Send to API
    await sendMessage(message);
}

async function sendMessage(message) {
    isStreaming = true;
    sendBtn.disabled = true;
    showStatus('Generating...');
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model: currentModel,
                messages: messages,
                message: message
            })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error: ${response.status}`);
        }
        
        // Handle streaming response
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        let assistantMessage = '';
        let tokenCount = 0;
        
        // Remove typing indicator and create assistant message element
        removeTypingIndicator();
        const messageEl = addMessage('assistant', '');
        
        while (true) {
            const { done, value } = await reader.read();
            
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.error) {
                            throw new Error(data.error);
                        }
                        
                        if (data.token) {
                            assistantMessage += data.token;
                            messageEl.querySelector('.message-content').textContent = assistantMessage;
                            tokenCount++;
                            
                            // Auto-scroll to bottom
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                    } catch (e) {
                        console.error('Parse error:', e);
                    }
                }
            }
        }
        
        // Update state
        messages.push({ role: 'assistant', content: assistantMessage });
        
        // Update status
        tokenCountEl.textContent = `${tokenCount} tokens`;
        showStatus('Ready');
        
    } catch (error) {
        console.error('Chat error:', error);
        removeTypingIndicator();
        addMessage('system', `Error: ${error.message}`);
        showStatus('Error', true);
    } finally {
        isStreaming = false;
        sendBtn.disabled = false;
        userInput.focus();
    }
}

// ============================================================================
// UI HELPERS
// ============================================================================

function addMessage(role, content) {
    const messageEl = document.createElement('div');
    messageEl.className = `message ${role}`;
    
    const contentEl = document.createElement('div');
    contentEl.className = 'message-content';
    contentEl.textContent = content;
    
    messageEl.appendChild(contentEl);
    
    if (role !== 'system') {
        const metaEl = document.createElement('div');
        metaEl.className = 'message-meta';
        metaEl.textContent = new Date().toLocaleTimeString();
        messageEl.appendChild(metaEl);
    }
    
    chatContainer.appendChild(messageEl);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    return messageEl;
}

function showTypingIndicator() {
    const typingEl = document.createElement('div');
    typingEl.className = 'message assistant';
    typingEl.id = 'typing-indicator';
    typingEl.innerHTML = `
        <div class="typing">
            <span></span>
            <span></span>
            <span></span>
        </div>
    `;
    chatContainer.appendChild(typingEl);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function removeTypingIndicator() {
    const typingEl = document.getElementById('typing-indicator');
    if (typingEl) {
        typingEl.remove();
    }
}

function clearChat() {
    messages = [];
    chatContainer.innerHTML = `
        <div class="message system">
            <div class="message-content">
                <p>👋 Chat cleared! Start a new conversation.</p>
            </div>
        </div>
    `;
    tokenCountEl.textContent = '';
    showStatus('Ready');
}

function showStatus(text, isError = false) {
    statusEl.textContent = text;
    statusEl.className = isError ? 'error' : '';
}

// ============================================================================
// ERROR HANDLING
// ============================================================================

window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
});

window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled rejection:', event.reason);
});
```

---

## Running the Application

### Development Mode

```bash
# Activate virtual environment
cd ~/ai-projects/chatbot
source venv/bin/activate

# Run the application
python3 app.py

# You should see:
# Running on http://0.0.0.0:5000
```

### Access the Chatbot

1. **On Jetson**: Open `http://localhost:5000` in a browser
2. **From another computer**: Find Jetson IP with `hostname -I`, then open `http://<IP>:5000`

### Verify Ollama is Running

```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Should return something like:
# {"models": [...]}
```

---

## Testing the Chatbot

### Basic Test

1. Open the chatbot in your browser
2. Type "Hello, how are you?"
3. Press Enter or click Send
4. Watch the response stream in real-time

### Model Switching Test

1. If you have multiple models installed
2. Use the dropdown to switch models
3. Send the same message to different models
4. Compare responses

### Error Handling Test

1. Stop Ollama: `pkill ollama`
2. Try to send a message
3. You should see an error message
4. Restart Ollama: `ollama serve`
5. Try again - should work

---

## Features Explained

### Streaming Responses

The chatbot uses Server-Sent Events (SSE) to stream tokens as they're generated:

```javascript
// Frontend: Read stream
const reader = response.body.getReader();
while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    // Process chunk...
}
```

### Model Selection

Models are fetched dynamically from Ollama:

```python
# Backend: Get models from Ollama
response = requests.get(f"{OLLAMA_BASE}/api/tags")
models = [m['name'] for m in response.json()['models']]
```

### Message History

Messages are stored in memory and included in each request:

```python
# Build prompt from history
prompt = ""
for msg in messages:
    prompt += f"{msg['role']}: {msg['content']}\n"
prompt += "assistant: "
```

---

## Security Considerations

### For Production

1. **Change the secret key**:
```bash
# Generate a secure key
python3 -c "import secrets; print(secrets.token_hex(32))"
```

2. **Set environment variables**:
```bash
export SECRET_KEY="your-generated-key"
export FLASK_ENV=production
```

3. **Use HTTPS** (via reverse proxy like nginx)

4. **Add authentication**:
```python
# Add to app.py
from flask_httpauth import HTTPBasicAuth
auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    return username == 'admin' and password == 'your-password'
```

---

## Production Deployment

### Using Gunicorn

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "app:app"
```

### Using Docker

```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
```

```bash
# Build and run
docker build -t chatbot .
docker run -d -p 5000:5000 --network host chatbot
```

### Using PM2

```bash
# Install PM2
sudo npm install -g pm2

# Create ecosystem file
cat > ecosystem.config.js << 'EOF'
module.exports = {
  apps: [{
    name: 'chatbot',
    script: 'app.py',
    interpreter: 'python3',
    instances: 2,
    env: {
      FLASK_ENV: 'production'
    }
  }]
};
EOF

# Start
pm2 start ecosystem.config.js
```

---

## Troubleshooting

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Connection refused" | Ollama not running | Run `ollama serve` |
| Model not found | Model not pulled | Run `ollama pull llama3.2` |
| Slow responses | Resource constraints | Close other apps, use smaller model |
| Memory error | Out of RAM | Use quantized models |

### Debug Mode

```python
# In app.py, set:
app.run(debug=True, ...)
```

This will show detailed error messages in the browser.

### Check Logs

```bash
# View application logs
tail -f logs/chatbot.log

# View Ollama logs
journalctl -u ollama -f
```

---

## Next Steps

Now that you have a basic chatbot, try these enhancements:

| Enhancement | Description | Difficulty |
|-------------|-------------|-------------|
| [Voice Input](02-voice-controlled-assistant.md) | Add speech-to-text | Medium |
| [RAG System](07-knowledge-base-rag.md) | Chat with your documents | Medium |
| [Vision](03-multimodal-vision-system.md) | Add image understanding | Hard |
| [Multi-Agent](13-multimodal-agent.md) | Multiple specialized agents | Hard |

---

## Related Documentation

- [Ollama API Documentation](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)

---

## License

MIT License
