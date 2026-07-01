# Project Nexus: Unified AI Operating System

## The Ultimate Local AI Platform for Jetson AGX Orin

This is the culmination of everything learned in the tutorial - a fully-featured AI operating system that combines all capabilities into a single, powerful application.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Features](#features)
3. [Prerequisites](#prerequisites)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Running the Application](#running-the-application)
7. [Web Interface Guide](#web-interface-guide)
8. [API Documentation](#api-documentation)
9. [Advanced Features](#advanced-features)
10. [Security](#security)
11. [Troubleshooting](#troubleshooting)
12. [Development](#development)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        PROJECT NEXUS ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                      WEB INTERFACE (Flask)                           │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │  │
│  │  │  Chat   │  │  Vision  │  │  Voice   │  │  RAG     │        │  │
│  │  │   UI    │  │   UI     │  │   UI     │  │   UI     │        │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘        │  │
│  └───────┼──────────────┼──────────────┼──────────────┼───────────────┘  │
│          │              │              │              │                   │
│  ┌──────┴──────────────┴──────────────┴──────────────┴──────────────┐   │
│  │                     NEXUS CORE ENGINE                            │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │   │
│  │  │  Agent   │  │ Session  │  │  Vector  │  │  Plugin  │   │   │
│  │  │Manager   │  │ Manager  │  │  Store   │  │  System  │   │   │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │   │
│  └───────┼──────────────┼──────────────┼──────────────┼───────────┘  │
│          │              │              │              │                │
│  ┌──────┴──────────────┴──────────────┴──────────────┴──────────────┐  │
│  │                     BACKEND CONNECTIONS                           │  │
│  │  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐              │  │
│  │  │Ollama  │  │llama.cpp│  │ MLC-LLM│  │External│              │  │
│  │  │ (REST) │  │ (gRPC)  │  │ (WS)   │  │  API   │              │  │
│  │  └────────┘  └────────┘  └────────┘  └────────┘              │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Features

### Core Features
- **Multi-Backend LLM Support**: Ollama, llama.cpp, MLC-LLM, custom endpoints
- **Vision Integration**: Camera capture, image analysis with LLaVA
- **Voice I/O**: Whisper STT and Piper TTS with wake word detection
- **RAG System**: Document ingestion, semantic search, chat with your data
- **Multi-Agent Orchestration**: Coordinated AI agents for complex tasks
- **Web UI**: Modern Flask-based interface accessible from any browser
- **REST API**: Full programmatic access to all features
- **Real-time Streaming**: Live token streaming for all LLM interactions
- **Session Management**: Persistent conversations with history
- **Plugin System**: Extensible architecture

### Advanced Features
- **Multi-Modal Chat**: Switch between text, voice, and vision seamlessly
- **Code Execution**: Sandboxed Python/JS code running
- **Web Search**: Real-time information retrieval
- **File Operations**: Upload, process, and analyze documents
- **System Control**: Execute shell commands (sandboxed)
- **Database Integration**: SQLite for persistence, optional PostgreSQL
- **Monitoring**: GPU/CPU/RAM tracking via WebSocket
- **Webhooks**: Event-driven integrations
- **Authentication**: Optional user management

---

## Prerequisites

### Hardware
- NVIDIA Jetson AGX Orin 64GB
- Webcam (for vision features)
- Microphone (for voice features)
- Speaker (for TTS output)

### Software
```bash
# Core requirements
sudo apt-get update
sudo apt-get install -y python3.10-venv python3-pip ffmpeg libsndfile1

# Python packages
pip3 install --upgrade pip
pip3 install flask flask-socketio flask-cors \
    langchain langchain-community langchain-ollama \
    chromadb sentence-transformers \
    opencv-python pillow pyaudio numpy scipy \
    pydantic pydantic-settings python-dotenv \
    aiohttp asyncio websockets \
    pillow-heif python-magic

# Install Ollama (if not already)
curl -fsSL https://ollama.ai/install.sh | sh
```

### Models Required
```bash
# Core models
ollama pull llama3.2
ollama pull nomic-embed-text

# Vision
ollama pull llava

# Speech
# Whisper installed separately
```

---

## Installation

### Step 1: Clone and Setup

```bash
cd ~
git clone https://github.com/yourusername/project-nexus.git
cd project-nexus
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Configure Environment

```bash
cp .env.example .env
nano .env
```

### Step 4: Initialize Database

```bash
python3 -m nexus.db.init
```

---

## Configuration

### Main Configuration File

Create `config.yaml`:

```yaml
# Project Nexus Configuration

app:
  name: "Project Nexus"
  version: "1.0.0"
  debug: false
  host: "0.0.0.0"
  port: 5000
  secret_key: "change-this-in-production"

security:
  api_key_required: false
  allowed_origins:
    - "*"
  max_request_size: 100MB
  rate_limit:
    enabled: true
    requests_per_minute: 60

ollama:
  base_url: "http://localhost:11434"
  default_model: "llama3.2"
  timeout: 120
  embedding_model: "nomic-embed-text"
  vision_model: "llava"

llama_cpp:
  enabled: false
  servers:
    - name: "qwen3-coder"
      url: "http://localhost:8080"
    - name: "glm-flash"
      url: "http://localhost:8081"

mlc:
  enabled: false
  websocket_url: "ws://localhost:8000/v1/chat"

whisper:
  model: "base"
  device: "cuda"
  language: "auto"

piper:
  model: "/usr/local/share/piper/samples/en_US-lessac-medium.onnx"
  config: "/usr/local/share/piper/samples/en_US-lessac-medium.onnx.json"

rag:
  vector_store: "chroma"
  persist_directory: "./data/chroma"
  chunk_size: 1000
  chunk_overlap: 200
  top_k: 5

storage:
  upload_folder: "./data/uploads"
  max_file_size: 50MB
  allowed_extensions:
    - ".txt"
    - ".md"
    - ".pdf"
    - ".docx"
    - ".pptx"
    - ".jpg"
    - ".png"
    - ".mp3"
    - ".mp4"

monitoring:
  metrics_enabled: true
  metrics_port: 9090
  websocket_updates: true

plugins:
  enabled: true
  directory: "./plugins"
  auto_load: true
```

### Environment Variables

Create `.env`:

```bash
# Flask
FLASK_APP=nexus.app:create_app
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-change-this

# Ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# Security
API_KEY=optional-api-key-for-external-access
ADMIN_PASSWORD=change-this-password

# Paths
DATA_DIR=./data
UPLOAD_DIR=./data/uploads
LOG_DIR=./logs

# Features
ENABLE_VISION=true
ENABLE_VOICE=true
ENABLE_RAG=true
ENABLE_CODE_EXEC=false

# Performance
MAX_WORKERS=4
GPU_LAYERS=35
CONTEXT_WINDOW=8192
```

---

## Running the Application

### Development Mode

```bash
# Activate environment
source venv/bin/activate

# Run with debug
python3 -m nexus.app --debug
```

### Production Mode

```bash
# Using Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 "nexus.app:create_app()"

# Or use the startup script
bash start.sh
```

### Docker Deployment

```bash
# Build
docker build -t project-nexus .

# Run
docker run -d \
  --name project-nexus \
  --runtime nvidia \
  -p 5000:5000 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config.yaml:/app/config.yaml \
  project-nexus
```

### Accessing from Windows/Mac

1. Find Jetson IP: `hostname -I`
2. Open browser: `http://<jetson-ip>:5000`
3. For external access, configure firewall or use VPN

---

## Web Interface Guide

### Dashboard

The main dashboard provides:
- System status (GPU, RAM, CPU)
- Active sessions
- Quick actions
- Recent activity

### Chat Interface

```
┌────────────────────────────────────────────────────────────────────────┐
│  🧠 Project Nexus                                    [Settings] [⚙]  │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  🤖 Assistant                                                  │  │
│  │     Hello! I'm your unified AI assistant. How can I help?      │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  👤 You                                                        │  │
│  │     Explain quantum computing in simple terms                  │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │  🤖 Assistant                                                  │  │
│  │     [Streaming response...]                                     │  │
│  └────────────────────────────────────────────────────────────────┘  │
│                                                                        │
├────────────────────────────────────────────────────────────────────────┤
│  [💬 Text] [🎤 Voice] [📷 Vision] [📄 RAG]  [Model: ▼ llama3.2]   │
│  ┌──────────────────────────────────────────────┐  [Send]            │
│  │ Type your message...                        │                    │
│  └──────────────────────────────────────────────┘                    │
└────────────────────────────────────────────────────────────────────────┘
```

### Mode Switching

| Mode | Icon | Features |
|------|------|----------|
| Text | 💬 | Standard chat |
| Voice | 🎤 | Voice input/output |
| Vision | 📷 | Camera/image analysis |
| RAG | 📄 | Document Q&A |

### Settings Panel

- Model selection
- Temperature/creativity
- System prompt customization
- Session management
- API key configuration

---

## API Documentation

### Authentication

```bash
# Using API Key
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:5000/api/v1/chat
```

### Endpoints

#### Chat

```bash
# Standard chat
curl -X POST http://localhost:5000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ],
    "stream": false
  }'

# Streaming chat
curl -X POST http://localhost:5000/api/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.2",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

#### Vision

```bash
# Analyze image
curl -X POST http://localhost:5000/api/v1/vision/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "image_url": "data:image/jpeg;base64,...",
    "prompt": "What do you see?"
  }'
```

#### RAG

```bash
# Add document
curl -X POST http://localhost:5000/api/v1/rag/documents \
  -F "file=@document.pdf"

# Query
curl -X POST http://localhost:5000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is in the document?",
    "top_k": 5
  }'
```

#### Voice

```bash
# Transcribe audio
curl -X POST http://localhost:5000/api/v1/voice/transcribe \
  -F "audio=@recording.mp3"

# Synthesize speech
curl -X POST http://localhost:5000/api/v1/voice/synthesize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, world!",
    "voice": "en_US-lessac-medium"
  }'
```

#### System

```bash
# Health check
curl http://localhost:5000/api/v1/health

# System stats
curl http://localhost:5000/api/v1/system/stats

# Model list
curl http://localhost:5000/api/v1/models
```

### WebSocket Events

Connect to `ws://localhost:5000/ws` for real-time updates:

```javascript
const ws = new WebSocket('ws://localhost:5000/ws');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.type, data.payload);
};
```

---

## Advanced Features

### Multi-Agent Orchestration

```python
# Configure agents in config.yaml
agents:
  - name: "researcher"
    model: "llama3.2"
    role: "Research specialist"
    tools: ["web_search", "file_read"]
    
  - name: "coder"
    model: "codeqwen"
    role: "Code generation"
    tools: ["code_execute"]
    
  - name: "analyst"
    model: "mathstral"
    role: "Data analysis"
    tools: ["calculator", "data_process"]
```

### Custom Plugins

Create `plugins/my_plugin.py`:

```python
from nexus.plugins import BasePlugin

class MyPlugin(BasePlugin):
    name = "my_plugin"
    version = "1.0.0"
    
    def initialize(self):
        self.register_command("hello", self.hello_world)
    
    async def hello_world(self, args):
        return "Hello from my plugin!"
```

### Code Execution

Enable in config:
```yaml
code_execution:
  enabled: true
  allowed_languages:
    - python
    - javascript
  timeout: 30
  max_output: 10000
```

### Webhooks

Configure webhooks:
```yaml
webhooks:
  events:
    - chat_completion
    - rag_query
    - voice_transcription
  endpoints:
    - url: "https://your-server.com/webhook"
      secret: "webhook-secret"
```

---

## Security

### Authentication Setup

```bash
# Set admin password
export ADMIN_PASSWORD="your-secure-password"

# Enable API key requirement
export API_KEY_REQUIRED=true
```

### SSL/HTTPS

```bash
# Generate certificate
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem \
  -days 365 -nodes

# Update config
ssl:
  enabled: true
  cert: "cert.pem"
  key: "key.pem"
```

### Network Security

```bash
# Allow specific IP
ALLOWED_IPS:
  - "192.168.1.0/24"

# Rate limiting
rate_limit:
  enabled: true
  per_minute: 60
  burst: 10
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Ollama not connecting | Check `OLLAMA_BASE_URL`, restart ollama service |
| CUDA out of memory | Reduce context size, use smaller models |
| Voice not working | Check microphone permissions, install ffmpeg |
| WebSocket disconnects | Check firewall, increase timeout settings |
| Slow responses | Run `sudo jetson_clocks`, check thermal throttling |

### Logs

```bash
# View logs
tail -f logs/nexus.log

# Debug mode
python3 -m nexus.app --debug --log-level=DEBUG
```

### Performance Tuning

```bash
# Maximum performance
sudo nvpmodel -m 0
sudo jetson_clocks

# Monitor
htop
jtop
```

---

## Development

### Project Structure

```
project-nexus/
├── nexus/
│   ├── __init__.py
│   ├── app.py              # Flask application
│   ├── config.py          # Configuration
│   ├── core/
│   │   ├── engine.py      # Main processing engine
│   │   ├── agents.py      # Agent system
│   │   ├── sessions.py   # Session management
│   │   └── plugins.py     # Plugin system
│   ├── api/
│   │   ├── chat.py       # Chat endpoints
│   │   ├── vision.py      # Vision endpoints
│   │   ├── voice.py      # Voice endpoints
│   │   └── rag.py        # RAG endpoints
│   ├── services/
│   │   ├── ollama.py     # Ollama client
│   │   ├── whisper.py    # STT service
│   │   ├── piper.py       # TTS service
│   │   └── vector.py     # Vector store
│   ├── web/
│   │   ├── routes.py     # Web routes
│   │   └── templates/    # HTML templates
│   └── utils/
│       ├── logger.py
│       └── security.py
├── config.yaml
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md
```

### Running Tests

```bash
pytest tests/
coverage run -m pytest
```

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes
4. Run tests
5. Submit pull request

---

## Credits

Built with ❤️ using:
- Flask & SocketIO
- LangChain
- Ollama
- Whisper
- Piper
- ChromaDB
- And many more...

---

## License

MIT License - See LICENSE file for details.
