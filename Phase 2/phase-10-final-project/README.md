# Phase 10: Final Project - Innovalabs Studio

This is the **capstone project** that combines everything you've learned in the previous phases into a complete, production-ready AI system.

---

## What is Innovalabs Studio?

**Innovalabs Studio** (Autonomous Literature Factory v1.0) is a comprehensive AI-powered research and content generation system that runs entirely on your Jetson AGX Orin.

### Features

- **Trend Scout** - AI-powered research assistant that monitors and analyzes trends
- **Literature Factory** - Automated content generation pipeline
- **Multi-model Support** - Uses Ollama, llama.cpp, and custom models
- **Workflow Automation** - n8n integration for automated pipelines
- **Google Sheets Integration** - Manage data via spreadsheets
- **Web Dashboard** - Full control via web interface

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Innovalabs Studio                         │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Trend      │  │  Literature  │  │   Content    │       │
│  │   Scout      │──│   Factory    │──│   Generator  │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                                   │                │
│         ▼                                   ▼                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              n8n Workflow Engine                      │   │
│  └──────────────────────────────────────────────────────┘   │
│         │                                   │                │
│         ▼                                   ▼                │
│  ┌──────────────┐                 ┌──────────────┐         │
│  │   Ollama     │                 │  llama.cpp   │         │
│  │  (LLMs)      │                 │  (GGUF)      │         │
│  └──────────────┘                 └──────────────┘         │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Web Dashboard (Flask)                   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Components

### 1. Trend Scout (`scripts_scout_trends.py`)
- AI-powered research assistant
- Monitors trends and generates insights
- Integrates with Google Sheets

### 2. Literature Factory (`INNOVALABS_Literature_Factory_v1.0.json`)
- n8n workflow for automated content creation
- Multi-step pipeline with AI agents
- Export to multiple formats

### 3. Web Dashboard
- **Flask-based** web interface
- Real-time monitoring
- Task management
- Model management

### 4. Docker Stack (`config_docker-compose.yml`)
- Containerized deployment
- All services pre-configured
- Easy startup and management

---

## Installation

### Prerequisites

- Jetson AGX Orin 64GB with JetPack 6.2.2
- Ubuntu 22.04.5 LTS
- CUDA 12.6, cuDNN 9.3, TensorRT 10.3

### Quick Install

```bash
cd phase-10-final-project/

# Make setup executable
chmod +x setup.sh

# Run installation
sudo ./setup.sh
```

### Manual Installation

See [INSTALL.md](INSTALL.md) for complete step-by-step instructions.

---

## Configuration

### Environment Variables

Copy and configure the environment file:

```bash
cp config_.env.example .env
# Edit .env with your settings
```

Key variables:
- `OLLAMA_HOST` - Ollama API endpoint
- `LLAMA_CPP_PORT` - llama.cpp server port
- `N8N_HOST` - n8n automation host
- `SHEETS_ENABLED` - Enable Google Sheets integration

### Docker Configuration

```bash
# Start all services
docker-compose -f config_docker-compose.yml up -d

# Check status
docker-compose -f config_docker-compose.yml ps
```

---

## Usage

### Starting the Dashboard

```bash
# Via Docker
docker-compose -f config_docker-compose.yml up -d dashboard

# Or directly
python3 dashboard_server.py
```

Access at: `http://jetson:5000`

### Running Trend Scout

```bash
python3 scripts_scout_trends.py --topic "AI trends" --depth 5
```

### Using n8n Workflows

1. Access n8n at `http://jetson:5678`
2. Import `INNOVALABS_Literature_Factory_v1.0.json`
3. Activate workflow

---

## Services & Ports

| Service | Port | Description |
|---------|------|-------------|
| Dashboard | 5000 | Web UI |
| Ollama | 11434 | LLM API |
| n8n | 5678 | Workflow automation |
| llama.cpp | 8080 | GGUF model API |

---

## Models Used

This project uses multiple models:

- **llama3.2** - General conversation
- **qwen2.5-coder** - Code generation
- **deepseek-r1** - Reasoning
- **mistral** - Fast inference
- **nomic-embed** - Text embeddings

---

## Troubleshooting

### Common Issues

**Dashboard won't start**
```bash
# Check logs
docker-compose logs dashboard

# Verify Python dependencies
pip3 install -r requirements.txt
```

**Models not loading**
```bash
# Restart Ollama
sudo systemctl restart ollama

# Verify GPU access
ollama list
```

**n8n workflow failing**
```bash
# Check n8n logs
docker-compose logs n8n

# Verify credentials
# Ensure .env is properly configured
```

---

## File Reference

| File | Description |
|------|-------------|
| `INSTALL.md` | Complete installation guide |
| `README_DOCKER.md` | Docker-specific instructions |
| `README_WORKFLOW.md` | Workflow documentation |
| `setup.sh` | Automated setup script |
| `verify_system.sh` | System verification |
| `dashboard_server.py` | Main Flask application |
| `config_docker-compose.yml` | Docker Compose configuration |

---

## What's Next?

Congratulations! You've completed the entire tutorial journey:

1. ✅ **Phase 1-2**: Set up your environment
2. ✅ **Phase 3-5**: Master core AI (LLMs, Speech, Vision)
3. ✅ **Phase 6-7**: Integration and production
4. ✅ **Phase 8-9**: Build projects
5. ✅ **Phase 10**: Deploy the final system

This project demonstrates:
- Full stack AI development
- Container orchestration
- Workflow automation
- Production deployment

**You're now a qualified Jetson AI Developer!**

---

## Support

For issues or questions:
- Check the detailed [INSTALL.md](INSTALL.md)
- Review [README_DOCKER.md](README_DOCKER.md)
- Check n8n workflow [README_WORKFLOW.md](README_WORKFLOW.md)

---

**Built with ❤️ on NVIDIA Jetson AGX Orin**
