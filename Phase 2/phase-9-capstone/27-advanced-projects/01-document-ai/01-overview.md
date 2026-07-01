# File Intelligence Hub - Overview

An AI-powered system that scans, enriches, and organizes your files using local RAG and intelligent duplicate detection.

## Features

- **Metadata Enrichment**: Extract and enhance metadata from documents
- **RAG Generation**: Create retrieval-augmented knowledge bases from your files
- **Duplicate Detection**: Identify similar and duplicate files using embeddings
- **Smart Recommendations**: Flag the newest/best version of duplicates
- **100% Local**: No cloud services, all processing on your Jetson

## Supported File Types

| Category | Formats |
|----------|---------|
| Documents | `.pdf`, `.docx`, `.doc`, `.txt`, `.rtf` |
| Spreadsheets | `.xlsx`, `.xls`, `.csv` |
| Presentations | `.pptx`, `.ppt` |
| E-books | `.epub`, `.mobi`, `.azw3` |
| Markdown | `.md`, `.markdown` |
| Code | `.py`, `.js`, `.java`, `.cpp`, etc. |

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    File Intelligence Hub                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │ File Scanner │───▶│  Metadata    │───▶│  Text Extractor│  │
│  │   Engine     │    │  Enricher    │    │                │  │
│  └──────────────┘    └──────────────┘    └───────┬───────┘  │
│                                                     │           │
│                                                     ▼           │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐  │
│  │  Duplicate   │◀───│   Embedding  │◀───│  RAG Generator │  │
│  │   Detector   │    │   Engine     │    │                │  │
│  └───────┬──────┘    └──────────────┘    └────────────────┘  │
│          │                                                       │
│          ▼                                                       │
│  ┌──────────────┐                                               │
│  │  Report      │                                               │
│  │  Generator   │                                               │
│  └──────────────┘                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Use Cases

### 1. Personal Document Organization
- Scan your Documents folder
- Generate embeddings for semantic search
- Find related documents automatically

### 2. Research Library Management
- Process academic papers
- Extract key concepts and topics
- Build a searchable knowledge base

### 3. Duplicate Cleanup
- Identify duplicate files across drives
- Compare content, not just filenames
- Recommend which copy to keep

### 4. USB/External Drive Indexing
- Scan portable drives
- Create portable knowledge bases
- Detect same files across devices

## Installation

```bash
# Create project directory
mkdir -p ~/file-intelligence
cd ~/file-intelligence

# Install dependencies
pip install -r requirements.txt

# Create necessary directories
mkdir -p data/cache data/embeddings data/reports logs

# Copy environment template
cp .env.example .env
```

## Requirements

```
# requirements.txt
ollama>=0.1.0
chromadb>=0.4.0
pypdf>=3.0.0
python-docx>=0.8.0
python-pptx>=0.6.0
epub2>=0.5.0
openpyxl>=3.0.0
python-magic>=0.4.0
tika>=1.19
sentence-transformers>=2.2.0
langchain>=0.1.0
langchain-community>=0.0.0
```

## Quick Start

```bash
# Enable performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Start Ollama in background
ollama serve &

# Pull required models
ollama pull nomic-embed-text
ollama pull qwen2.5-coder

# Run initial scan
python main.py scan --path /path/to/documents

# Generate RAG
python main.py index --rebuild

# Find duplicates
python main.py duplicates --path /path/to/scan
```

## Configuration

Edit `.env` file:

```bash
# Ollama Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder
EMBEDDING_MODEL=nomic-embed-text

# Processing
MAX_FILE_SIZE=100MB
BATCH_SIZE=10
PARALLEL_WORKERS=4

# Duplicate Detection
SIMILARITY_THRESHOLD=0.85
MIN_DUPLICATE_SIZE=1KB

# Paths
SCAN_PATHS=/home/jetson/Documents,/media/usb
EXCLUDE_PATHS=.git,node_modules,__pycache__
```

## Next Steps

- [File Scanning Engine](./02-file-scanning-engine.md) - Core scanning implementation
- [RAG & Duplicate Detection](./03-rag-duplicate-detection.md) - Embedding and similarity
- [GraphRAG Implementation](./04-graphrag-implementation.md) - Knowledge graph approach
