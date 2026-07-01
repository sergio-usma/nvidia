# Part 28: Advanced Integration Projects

This part covers production-ready AI applications that run completely locally on your Jetson AGX Orin.

## Projects Overview

| # | Project | Description | Complexity |
|---|---------|-------------|------------|
| 1 | **File Intelligence Hub** | AI-powered file metadata enrichment, RAG, and duplicate detection | Advanced |
| 2 | **Yacht Jobs Automation** | Automated job search, AI processing, and LinkedIn publishing | Intermediate |
| 3 | **Ebook Summary Factory** | Multi-agent ebook processing with professional summaries | Advanced |
| 4 | **AI Image Generation Studio** | Text-to-image with ComfyUI + Ollama prompt enhancement | Advanced |
| 5 | **AI Audio Generation Studio** | Text-to-speech with Piper + Ollama text processing | Intermediate |
| 6 | **AI Video Generation Studio** | Story-to-video with frame generation + FFmpeg | Advanced |
| 7 | **INNOVALABS Literature Factory** | Autonomous multi-agent storytelling pipeline | Advanced |
| 8 | **Funding Finder** | Autonomous funding proposal generator with 6+ AI agents | Advanced |
| 9 | **AI Office** | Virtual AI team with 6 specialized agents working 24/7 | Advanced |

## Folder Structure

```
part-28-integration-advanced-projects/
├── README.md
│
├── 01-file-intelligence/
│   ├── 01-overview.md        # Project overview
│   ├── 02-implementation.md  # File scanning engine
│   ├── 03-rag.md            # RAG & duplicate detection
│   ├── 04-graphrag.md       # GraphRAG implementation
│   └── 05-commands.md      # Usage commands
│
├── 02-yacht-jobs/
│   ├── 01-overview.md        # Project overview
│   ├── 02-scraper.md        # Job scraper
│   ├── 03-ai-processing.md # AI categorization
│   ├── 04-n8n.md           # n8n orchestration
│   └── 05-linkedin.md      # LinkedIn publishing
│
├── 03-ebook-summary/
│   ├── 01-overview.md       # Project overview
│   ├── 02-processor.md     # EPUB processor
│   ├── 03-agents.md        # Multi-agent system
│   ├── 04-summary.md       # Summary generation
│   └── 05-deployment.md    # Production deployment
│
├── 04-image-studio/
│   └── 01-image-studio.md
│
├── 05-audio-studio/
│   └── 01-audio-studio.md
│
├── 06-video-studio/
│   └── 01-video-studio.md
│
└── 07-innovalabs-factory/
    ├── 01-overview.md          # Project overview
    ├── 02-installation.md     # Detailed installation
    ├── 03-agents.md           # AI agents configuration
    ├── 04-pipeline.md         # Pipeline configuration
    └── 05-deployment.md       # Deployment & maintenance
```
part-28-integration-advanced-projects/
├── 01-file-intelligence/
│   ├── README.md           # Overview
│   ├── implementation.md   # File scanning engine
│   ├── rag.md             # RAG & duplicate detection
│   ├── graphrag.md        # GraphRAG implementation
│   └── commands.md        # Usage commands
│
├── 02-yacht-jobs/
│   ├── README.md           # Overview
│   ├── scraper.md          # Job scraper
│   ├── ai-processing.md    # AI categorization
│   ├── n8n.md             # n8n orchestration
│   └── linkedin.md        # LinkedIn publishing
│
├── 03-ebook-summary/
│   ├── README.md           # Overview
│   ├── processor.md        # EPUB processor
│   ├── agents.md           # Multi-agent system
│   ├── summary.md          # Summary generation
│   └── deployment.md       # Production deployment
│
├── 04-image-studio/
│   └── README.md           # Image generation studio
│
├── 05-audio-studio/
│   └── README.md           # Audio generation studio
│
├── 06-video-studio/
│   └── README.md           # Video generation studio
│
└── README.md               # This file
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     Part 28 - Advanced Integration                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────────────┐ │
│  │  01 File          │ │  02 Yacht Jobs    │ │  03 Ebook Summary         │ │
│  │  Intelligence     │ │                   │ │                           │ │
│  │  ├─ Metadata      │ │  ├─ Scraper       │ │  ├─ EPUB Processor       │ │
│  │  ├─ RAG           │ │  ├─ AI Processing │ │  ├─ Multi-Agent          │ │
│  │  └─ GraphRAG      │ │  ├─ n8n           │ │  └─ Summary Gen          │ │
│  └─────────┬─────────┘ └─────────┬─────────┘ └─────────────┬─────────────┘ │
│            │                    │                         │               │
│  ┌────────┴────────────────────┴─────────────────────────┴─────────────┐ │
│  │                    Media Generation Studios                          │ │
│  ├──────────────┬──────────────┬────────────────────────────────────────┤ │
│  │  04 Image    │  05 Audio   │  06 Video                             │ │
│  │  ├─ ComfyUI  │  ├─ Piper   │  ├─ Story Splitting (Ollama)          │ │
│  │  └─ Ollama   │  └─ Ollama  │  ├─ Frame Gen (ComfyUI)               │ │
│  │     Prompts │    Text      │  └─ FFmpeg Encoding                   │ │
│  └─────────────┴─────────────┴────────────────────────────────────────┘ │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────────┐ │
│  │                    Ollama / llama.cpp                                │ │
│  │                    (Local AI Models)                                 │ │
│  └──────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

All projects require:

- Jetson AGX Orin with JetPack 6.2+
- Ollama installed with preferred models
- At least 32GB RAM recommended
- Sufficient storage for models/data

### Media Generation Additional Requirements

```bash
# ComfyUI (for image/video)
source ~/comfyui_env/bin/activate
cd ~/ComfyUI
python3 main.py --listen 0.0.0.0 --port 8188 --enable-api &

# Piper TTS (for audio)
sudo apt install -y piper

# FFmpeg (for video)
sudo apt install -y ffmpeg
```

### Port Assignments

| Service | Port | Description |
|---------|------|-------------|
| ComfyUI | 8188 | Image/Video generation UI & API |
| Image Studio API | 8080 | REST API for image generation |
| Audio Studio API | 8081 | REST API for audio generation |
| Video Studio API | 8082 | REST API for video generation |
| Ollama | 11434 | Local LLM API |

## Hardware Optimization

For all projects, ensure maximum performance:

```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

## Model Recommendations

| Project | Primary Model | Notes |
|---------|--------------|-------|
| File Intelligence | qwen2.5-coder:14b | Good for embeddings |
| Yacht Jobs | llama3.2:3b | Fast, efficient |
| Ebook Summary | qwen2.5-coder:14b | Good reasoning |
| Image/Audio/Video Studio | llama3.2:3b | Prompt enhancement |

## Network Access (Media Studios)

### Option 1: Direct IP
```
http://<JETSON_IP>:8080  # Image
http://<JETSON_IP>:8081  # Audio
http://<JETSON_IP>:8082  # Video
```

### Option 2: Nginx Reverse Proxy
```
https://image.yourhostname.local
https://audio.yourhostname.local
https://video.yourhostname.local
```

### Option 3: SSH Tunnel
```bash
ssh -L 8080:localhost:8080 -L 8081:localhost:8081 -L 8082:localhost:8082 sergiok@<JETSON_IP>
```

## Quick Navigation

### Project 1: File Intelligence Hub
- [01-overview](./01-file-intelligence/01-overview.md)
- [02-implementation](./01-file-intelligence/02-implementation.md)
- [03-rag](./01-file-intelligence/03-rag.md)
- [04-graphrag](./01-file-intelligence/04-graphrag.md)
- [05-commands](./01-file-intelligence/05-commands.md)

### Project 2: Yacht Jobs Automation
- [01-overview](./02-yacht-jobs/01-overview.md)
- [02-scraper](./02-yacht-jobs/02-scraper.md)
- [03-ai-processing](./02-yacht-jobs/03-ai-processing.md)
- [04-n8n](./02-yacht-jobs/04-n8n.md)
- [05-linkedin](./02-yacht-jobs/05-linkedin.md)

### Project 3: Ebook Summary Factory
- [01-overview](./03-ebook-summary/01-overview.md)
- [02-processor](./03-ebook-summary/02-processor.md)
- [03-agents](./03-ebook-summary/03-agents.md)
- [04-summary](./03-ebook-summary/04-summary.md)
- [05-deployment](./03-ebook-summary/05-deployment.md)

### Project 4: AI Image Generation Studio
- [01-image-studio](./04-image-studio/01-image-studio.md)

### Project 5: AI Audio Generation Studio
- [01-audio-studio](./05-audio-studio/01-audio-studio.md)

### Project 6: AI Video Generation Studio
- [01-video-studio](./06-video-studio/01-video-studio.md)

### Project 7: INNOVALABS Literature Factory
- [01-overview](./07-innovalabs-factory/01-overview.md)
- [02-installation](./07-innovalabs-factory/02-installation.md)
- [03-agents](./07-innovalabs-factory/03-agents.md)
- [04-pipeline](./07-innovalabs-factory/04-pipeline.md)
- [05-deployment](./07-innovalabs-factory/05-deployment.md)

### Project 8: Funding Finder
- [01-overview](./08-funding-finder/01-overview.md)
- [02-scraping](./08-funding-finder/02-scraping.md)
- [03-sheets](./08-funding-finder/03-sheets.md)
- [04-documents](./08-funding-finder/04-documents.md)
- [05-agents](./08-funding-finder/05-agents.md)
- [06-dashboard](./08-funding-finder/06-dashboard.md)
- [07-delivery](./08-funding-finder/07-delivery.md)
- [08-installation](./08-funding-finder/08-installation.md)
