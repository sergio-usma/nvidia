# Project Nexus - Node.js Edition

A unified AI platform for NVIDIA Jetson AGX Orin built with Node.js, Express, and Socket.IO.

## Features

- **Real-time Chat**: Streaming responses via Socket.IO with session management
- **Vision API**: Image analysis endpoint (configure LLaVA for full functionality)
- **Voice Input**: Speech-to-text interface (configure Whisper for transcription)
- **RAG Pipeline**: Document upload and knowledge base querying
- **System Monitoring**: Real-time GPU, memory, and CPU stats
- **Multi-model Support**: Works with all Ollama models

## Requirements

- Node.js 18+
- Ollama running on port 11434
- NVIDIA Jetson AGX Orin (or any Linux system with Ollama)

## Installation

```bash
cd final-project/nodejs
npm install
```

## Running

```bash
npm start
```

The server will start on `http://localhost:5000`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| PORT | 5000 | Server port |
| OLLAMA_URL | http://localhost:11434 | Ollama API URL |
| DEFAULT_MODEL | llama3.2 | Default model |
| DATA_DIR | ./data | Data directory |
| UPLOAD_DIR | ./data/uploads | Upload directory |

## API Endpoints

### System
- `GET /health` - Health check
- `GET /api/v1/system/stats` - System statistics

### Models
- `GET /api/v1/models` - List available models

### Chat
- `POST /api/v1/chat` - Send chat message
- `POST /api/v1/chat/completions` - OpenAI-compatible completions

### Sessions
- `GET /api/v1/sessions` - List sessions
- `POST /api/v1/sessions` - Create session
- `DELETE /api/v1/sessions/:id` - Delete session

### RAG
- `POST /api/v1/rag/documents` - Upload document
- `POST /api/v1/rag/query` - Query knowledge base

### Search
- `POST /api/v1/search` - Web search (requires ddgr)

## Web Interface

- `/` - Dashboard with system stats
- `/chat.html` - Chat interface
- `/vision.html` - Image analysis
- `/voice.html` - Voice input
- `/rag.html` - Document upload & query
- `/monitor.html` - Real-time monitoring

## Socket.IO Events

### Client → Server
- `chat_message` - Send chat message
- `create_session` - Create new session
- `vision_analyze` - Analyze image
- `system_stats` - Request stats

### Server → Client
- `stream_chunk` - Streaming response
- `chat_response` - Complete response
- `session_created` - Session created
- `vision_result` - Vision analysis result
- `system_stats` - System statistics

## Example Usage

```javascript
// Chat via API
const response = await fetch('http://localhost:5000/api/v1/chat', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    message: 'Hello!',
    model: 'llama3.2'
  })
});
const data = await response.json();
console.log(data.response);

// Or with Socket.IO
const socket = io('http://localhost:5000');
socket.emit('chat_message', { message: 'Hello!' });
socket.on('stream_chunk', (chunk) => process.stdout.write(chunk.token));
```

## Production Deployment

For production, consider:
- Running behind a reverse proxy (nginx)
- Adding SSL/TLS
- Implementing authentication
- Using PM2 for process management
- Setting up proper logging

```bash
# Install PM2
sudo npm install -g pm2

# Start with PM2
pm2 start server.js --name nexus

# Auto-start on boot
pm2 startup
pm2 save
```

## Architecture

```
public/
├── index.html      # Dashboard
├── chat.html       # Chat interface
├── vision.html     # Vision analysis
├── voice.html      # Voice input
├── rag.html        # RAG interface
└── monitor.html    # System monitoring

server.js           # Express + Socket.IO server
package.json        # Dependencies
```

## License

MIT
