# Part 14: Final Project - Project Nexus

This is the culmination of everything learned throughout the tutorial - a unified AI operating system that combines all capabilities into a single, powerful application.

## What is Project Nexus?

Project Nexus is a comprehensive AI platform that brings together:
- **Multi-Backend LLM Support**: Ollama, llama.cpp, MLC-LLM
- **Vision Integration**: Camera capture, image analysis with LLaVA
- **Voice I/O**: Whisper STT and Piper TTS with wake word detection
- **RAG System**: Document ingestion, semantic search, chat with your data
- **Real-time Web Interface**: Modern browser-based UI
- **REST API**: Full programmatic access to all features
- **Multi-Agent Orchestration**: Coordinated AI agents for complex tasks

---

## Choose Your Implementation

| Implementation | Technology | Best For |
|----------------|------------|----------|
| [Python Version](python/) | Flask + Socket.IO | LangChain integration, Python ecosystems |
| [Node.js Version](nodejs/) | Express + Socket.IO | Real-time apps, JavaScript ecosystems |

---

## Hardware Requirements

- **Jetson AGX Orin 64GB** (recommended)
- 32GB also works with optimized models
- Webcam (for vision features)
- Microphone (for voice features)
- Speaker (for TTS output)

---

## Quick Start

### Python Version

```bash
cd python
pip3 install -r requirements.txt
python3 -m nexus.app
# Open http://localhost:5000
```

### Node.js Version

```bash
cd nodejs
npm install
npm start
# Open http://localhost:5000
```

---

## Features Comparison

| Feature | Python | Node.js |
|---------|--------|---------|
| Chat UI | ✅ | ✅ |
| Vision Analysis | ✅ | ✅ |
| Voice Input | ✅ | ✅ |
| RAG/Documents | ✅ | ✅ |
| System Monitoring | ✅ | ✅ |
| Socket.IO Streaming | ✅ | ✅ |
| LangChain Integration | ✅ | ❌ |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│              Project Nexus Architecture             │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────────────┐  │
│  │            Web Interface (UI)               │  │
│  │  Dashboard │ Chat │ Vision │ Voice │ RAG    │  │
│  └──────────────────────┬──────────────────────┘  │
│                         │                          │
│  ┌──────────────────────┴──────────────────────┐  │
│  │           Backend Server                    │  │
│  │  Flask/Express + Socket.IO                  │  │
│  └──────────────────────┬──────────────────────┘  │
│                         │                          │
│  ┌──────────────────────┴──────────────────────┐  │
│  │           Core Services                     │  │
│  │  Ollama │ Whisper │ Piper │ ChromaDB        │  │
│  └─────────────────────────────────────────────┘  │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Prerequisites

Before starting, complete these tutorials:

1. [Part 1: System Setup](../part-1-system-setup/)
2. [Part 3: Python Environment](../part-3-python-environment/)
3. [Part 4: Node.js](../part-4-nodejs/)
4. [Part 5: LLMs (Ollama)](../part-5-llms/)
5. [Part 6: Speech/Audio](../part-6-speech-audio/)
6. [Part 7: Vision](../part-7-vision/)

---

## Required Models

```bash
# Core chat model
ollama pull llama3.2

# Embeddings for RAG
ollama pull nomic-embed-text

# Vision model
ollama pull llava
```

---

## Configuration

Both versions support configuration via environment variables:

```bash
# Required
OLLAMA_BASE_URL=http://localhost:11434
DEFAULT_MODEL=llama3.2

# Optional
PORT=5000
ENABLE_VISION=true
ENABLE_VOICE=true
ENABLE_RAG=true
```

---

## API Endpoints

Both implementations provide similar REST APIs:

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /api/v1/models` | List available models |
| `POST /api/v1/chat` | Send chat message |
| `POST /api/v1/chat/completions` | OpenAI-compatible API |
| `POST /api/v1/vision/analyze` | Analyze image |
| `POST /api/v1/voice/transcribe` | Transcribe audio |
| `POST /api/v1/rag/query` | Query knowledge base |
| `GET /api/v1/system/stats` | System statistics |

---

## WebSocket Events

Real-time streaming via Socket.IO:

| Event | Direction | Description |
|-------|-----------|-------------|
| `chat_message` | Client→Server | Send message |
| `stream_chunk` | Server→Client | Token streaming |
| `system_stats` | Server→Client | Live stats |

---

## Performance Tips

1. **Use MAXN mode**: `sudo nvpmodel -m 0 && sudo jetson_clocks`
2. **Monitor resources**: Keep `jtop` running
3. **Optimize models**: Use quantization for faster inference
4. **Manage memory**: Close unused sessions

---

## Security

For production deployment:

1. Set `SECRET_KEY` and `ADMIN_PASSWORD`
2. Enable SSL/TLS with nginx reverse proxy
3. Implement rate limiting
4. Configure allowed IPs
5. Use firewall rules

---

## Next Steps

After completing Project Nexus:
- Explore [Part 11: Projects](../part-11-projects/) for additional applications
- Try [Part 15: Bonus Projects](../part-15-bonus-projects/) for fun AI games
- Build your own custom plugins and integrations

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Ollama not connecting | Check `OLLAMA_BASE_URL`, restart service |
| CUDA out of memory | Reduce context size, use smaller models |
| Voice not working | Check microphone permissions |
| Slow responses | Run `sudo jetson_clocks`, check thermal throttling |

---

## Credits

Built with:
- Flask / Express
- Socket.IO
- LangChain
- Ollama
- Whisper
- Piper
- ChromaDB

---

## License

MIT License
