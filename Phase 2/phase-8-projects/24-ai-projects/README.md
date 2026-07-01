# Projects Index

This section contains hands-on projects that combine everything you've learned from the previous tutorials. Each project is designed to reinforce your understanding while creating useful applications.

## Project List

| Project | Description | Skills Used |
|---------|-------------|-------------|
| [01-local-ai-chatbot](01-local-ai-chatbot.md) | Build a complete AI chatbot web interface | Docker, Ollama, Web development |
| [02-voice-controlled-assistant](02-voice-controlled-assistant.md) | Voice-controlled AI assistant with wake word | Whisper, Ollama, Piper |
| [03-multimodal-vision-system](03-multimodal-vision-system.md) | AI system that sees and describes | LLaVA, Camera integration |
| [04-coding-assistant-setup](04-coding-assistant-setup.md) | Set up AI pair programmer with VS Code | Continue, Ollama, VS Code |
| [05-home-automation-bridge](05-home-automation-bridge.md) | Connect AI to Home Assistant via MQTT | MQTT, Voice commands |
| [06-security-camera-ai](06-security-camera-ai.md) | AI-powered security camera with detection | Object detection, Alerts |
| [07-knowledge-base-rag](07-knowledge-base-rag.md) | Build RAG system for your documents | Embeddings, Vector DB |
| [08-ai-api-server](08-ai-api-server.md) | Create production-ready AI API server | FastAPI, Ollama, Security |

## Advanced Projects (Optimized for Jetson AGX Orin 64GB)

| Project | Description | Hardware Optimization |
|---------|-------------|---------------------|
| [09-tensorrt-llm-server](09-tensorrt-llm-server.md) | TensorRT-optimized LLM inference with FP16/INT8 | CUDA 12.6, TensorRT 10.3, 64GB RAM |
| [10-multi-camera-analytics](10-multi-camera-analytics.md) | Multi-camera video analytics with DeepStream | NVDEC, TensorRT, 4+ streams |
| [11-realtime-tracking](11-realtime-tracking.md) | Real-time object tracking with DeepSort | CUDA, YOLO, Kalman filtering |
| [12-voice-pipeline](12-voice-pipeline.md) | End-to-end voice AI pipeline | Whisper, Piper, Wake word |
| [13-multimodal-agent](13-multimodal-agent.md) | Multimodal AI agent (vision + voice + reasoning) | LLaVA, Ollama, 64GB RAM |
| [14-distributed-cluster](14-distributed-cluster.md) | Distributed inference cluster | Multi-node, Load balancing |
| [15-video-streaming](15-video-streaming.md) | Real-time video streaming with AI overlays | NVENC, HLS, WebSocket |
| [16-production-dashboard](16-production-dashboard.md) | Production monitoring dashboard | Prometheus, Grafana, Alerts |

## How to Use These Projects

1. **Start with Project 1** if you're new - it's the most comprehensive
2. Projects are listed roughly in order of complexity
3. Each project includes:
   - Prerequisites (which tutorials to complete first)
   - Step-by-step instructions
   - Complete code examples
   - Testing and verification steps

## Before Starting Any Project

Make sure you have:
- Completed [Part 1: System Setup](../part-1-system-setup/)
- Installed [Ollama](../part-5-llms/01-ollama-setup.md)
- Understood [Docker basics](../part-2-docker/)

---

## Choosing Your First Project

| If you want to... | Start with |
|------------------|-----------|
| Build a web UI for AI | Project 1: Local AI Chatbot |
| Talk to AI with your voice | Project 2: Voice Assistant |
| Give AI eyes | Project 3: Multimodal Vision |
| AI help while coding | Project 4: Coding Assistant |
| Control smart home with AI | Project 5: Home Automation |
| AI security camera | Project 6: Security Camera |
| Ask AI about your files | Project 7: Knowledge Base RAG |
| Build an API for AI | Project 8: AI API Server |
| **Maximum LLM performance** | Project 9: TensorRT-LLM Server |
| **Multi-camera analytics** | Project 10: Multi-Camera Analytics |
| **Real-time tracking** | Project 11: Real-Time Tracking |
| **Complete voice AI** | Project 12: Voice Pipeline |
| **Combined vision+voice** | Project 13: Multimodal Agent |
| **Scale across devices** | Project 14: Distributed Cluster |
| **Live video streaming** | Project 15: Video Streaming |
| **Monitor everything** | Project 16: Production Dashboard |

---

## Project Tips

1. **Read through once** before starting
2. **Test each component** separately before combining
3. **Keep jtop running** to monitor resource usage
4. **Start small** - use smaller models first
5. **Document your changes** - you'll want to remember what worked

Good luck and happy building!
