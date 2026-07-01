# Funding Finder - Autonomous Project Proposal Generator

## Project Overview

The Funding Finder is an autonomous AI system that continuously searches for worldwide funding opportunities, grants, and open calls applicable to Colombia. It scrapes public websites, downloads documentation, analyzes requirements, and generates complete project proposals using a multi-agent RAG system.

### What It Does

1. **Scraping** - Searches worldwide for funding opportunities using Scrapling
2. **Monitoring** - Tracks all opportunities in Google Sheets
3. **Document Collection** - Downloads PDFs, DOCX, XLSX from open calls
4. **Analysis** - Reads terms, calendar, goals using local AI
5. **Proposal Generation** - Creates full project proposals with 6+ AI agents
6. **Dashboard** - 16-bit animated office with real-time agent status
7. **Delivery** - Sends complete proposals via email and Google Drive
8. **Autonomous** - Runs 24/7 without human intervention

### Features

- **Real-time Scraping**: Scrapling-based web crawler for funding opportunities
- **Colombia Focus**: Filters opportunities available for Colombian entities
- **Multi-Category**: Social, educational, technological, environmental, tourism, etc.
- **RAG System**: Retrieval-augmented generation using downloaded documents
- **Multi-Agent Pipeline**: 6+ specialized AI agents working simultaneously
- **Animated Dashboard**: 16-bit pixel art office showing agents at work
- **Remote Control**: Control workflow from Windows/Mac via browser
- **Auto-Delivery**: Email + Google Drive with full documentation

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    FUNDING FINDER SYSTEM                                     │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    SCRAPER AGENTS (Parallel)                         │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐               │  │
│  │  │ Colombia │ │   Gov    │ │   EU     │ │  Global  │               │  │
│  │  │  Sites   │ │   Fund   │ │   Fund   │ │   Fund   │               │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘               │  │
│  └───────┼────────────┼────────────┼────────────┼───────────────────────┘  │
│          │            │            │            │                           │
│          └────────────┴────────────┼────────────┘                           │
│                                   │                                         │
│  ┌────────────────────────────────▼────────────────────────────────────┐  │
│  │                    GOOGLE SHEETS QUEUE                               │  │
│  │         ID │ Title │ Category │ Status │ Deadline │ Budget          │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                   │                                         │
│          ┌────────────────────────┼────────────────────────┐              │
│          │                        │                        │              │
│          ▼                        ▼                        ▼              │
│  ┌─────────────┐        ┌─────────────┐        ┌─────────────┐         │
│  │  DOWNLOAD   │        │   ANALYZE   │        │   CREATE    │         │
│  │   AGENT     │        │    AGENT     │        │   FOLDERS   │         │
│  │             │        │             │        │    AGENT     │         │
│  │ • PDFs      │        │ • Read PDF  │        │ • By topic  │         │
│  │ • DOCX      │        │ • Extract   │        │ • By date   │         │
│  │ • XLSX      │        │ • Requirements│      │ • By agency │         │
│  └─────────────┘        └─────────────┘        └─────────────┘         │
│                                   │                                         │
│  ┌────────────────────────────────▼────────────────────────────────────┐  │
│  │                    RAG KNOWLEDGE BASE                               │  │
│  │         ChromaDB with document embeddings                          │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                   │                                         │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │              PROPOSAL GENERATION AGENTS (Parallel)                  │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │  │
│  │  │ Project │ │ Technical│ │ Budget  │ │Compliance│ │ Final   │      │  │
│  │  │  Lead   │ │  Writer │ │ Expert  │ │ Analyst │ │ Reviewer│      │  │
│  │  └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘      │  │
│  │       └────────────┴────────────┴────────────┘              │         │
│  └───────────────────────────────────────────────────────────────┼────────┘  │
│                                                                  │          │
│  ┌───────────────────────────────────────────────────────────────▼────────┐  │
│  │                       DELIVERY SYSTEM                            │       │
│  │  ┌──────────────────┐    ┌──────────────────┐                 │       │
│  │  │  EMAIL (SMTP)    │    │  GOOGLE DRIVE    │                 │       │
│  │  │  +ZIP attachment │    │  +Folder upload  │                 │       │
│  │  └──────────────────┘    └──────────────────┘                 │       │
│  └────────────────────────────────────────────────────────────────┘       │
│                                                                          │
└──────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                         DASHBOARD (Port 8090)                              │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │   ████████ 16-BIT OFFICE ANIMATION ██████████████████████████████  │   │
│  │                                                                     │   │
│  │   [Agent1 PC] [Agent2 PC] [Agent3 PC] [Agent4 PC] [Agent5 PC]      │   │
│  │   ░░░░░░░░ ░░░░░░░░ ░░░░░░░░ ░░░░░░░░ ░░░░░░░░                    │   │
│  │   ░░WORK░░ ░░IDLE░░ ░░WORK░░ ░░WAIT░░ ░░WORK░░                    │   │
│  │                                                                     │   │
│  │   [POKEMON-STYLE PLATFORM - Drag & Drop Agents]                    │   │
│  │   ⚔️ Scraper ⚔️ Analyzer ⚔️ Writer ⚔️ Budget ⚔️ Compliance         │   │
│  │                                                                     │   │
│  │   📊 Active Jobs: 3  │  📁 Queued: 12  │  ✅ Completed: 47        │   │
│  │                                                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Prerequisites

### Hardware

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| Device | Jetson AGX Orin 64GB | Jetson AGX Orin 64GB |
| RAM | 32GB | 64GB |
| Storage | 256GB | 512GB NVMe |
| GPU | 16GB VRAM | 32GB (with swap) |

### Software

- Ubuntu 22.04 LTS (aarch64)
- JetPack 6.2+
- Docker + NVIDIA Container Toolkit
- Ollama (multiple models)
- Node.js 20 + n8n
- Python 3.10+
- Scrapling
- Nginx

### Models Required

| Model | Purpose | Size | Source |
|-------|---------|------|--------|
| qwen2.5-coder:14b | Document analysis | ~9GB | Ollama |
| llama3.2:3b | General tasks | ~4GB | Ollama |
| nomic-embed-text | Embeddings | ~1GB | Ollama |
| glm-4.7-flash | Fast generation | ~3GB | Ollama |
| deepseek-r1:8b | Reasoning | ~5GB | Ollama |

## System Components

### 1. Scraper Agents

Multiple parallel scrapers targeting different sources:

- **Colombia Gov Sites**: colciencias, icolven, findeter, bancoldex
- **International**: EU CORDIS, UNDP, World Bank, IDB
- **Private Foundations**: Ford, Gates, Rockefeller
- **General**: Google Alerts, RSS feeds

### 2. Analysis Agents

- Document download and conversion
- PDF/DOCX/XLSX parsing
- Requirement extraction
- Deadline tracking

### 3. Proposal Generation Agents

| Agent | Role | Model |
|-------|------|-------|
| **Project Lead** | Defines project vision and objectives | qwen2.5-coder:14b |
| **Technical Writer** | Creates technical documentation | llama3.2:3b |
| **Budget Expert** | Builds financial projections | glm-4.7-flash |
| **Compliance Analyst** | Ensures requirement adherence | deepseek-r1:8b |
| **Legal Reviewer** | Checks legal constraints | qwen2.5-coder:14b |
| **Final Reviewer** | Quality assurance | llama3.2:3b |

### 4. Delivery System

- SMTP email with ZIP attachment
- Google Drive folder creation
- Structured folder hierarchy

## Next Steps

- [02-scraping](./02-scraping.md) - Web scraping configuration
- [03-sheets](./03-sheets.md) - Google Sheets integration
- [04-documents](./04-documents.md) - Document processing & RAG
- [05-agents](./05-agents.md) - Multi-agent system
- [06-dashboard](./06-dashboard.md) - Animated dashboard
- [07-delivery](./07-delivery.md) - Email & Google Drive
- [08-installation](./08-installation.md) - Setup guide
