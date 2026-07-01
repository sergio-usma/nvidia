# Ebook Summarizer Overview

A production-ready system to process large ebook libraries (200k+ books) and generate professional summaries using multi-agent AI architecture.

## Features

- **Multi-Agent Processing**: 5+ specialized agents working in parallel
- **Professional Summaries**: Bullet points + key insights
- **5% Synthesis**: Average summary is 5% of original page count
- **Multiple Formats**: Export to Markdown, PDF, Audio
- **100% Local**: All processing on your Jetson
- **Scalable**: Designed for 200k+ books

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Ebook Summary Factory                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐      │
│  │   Scanner   │───▶│   Parser     │───▶│   Splitter    │      │
│  │   Agent     │    │   Agent      │    │   Agent       │      │
│  └──────────────┘    └──────────────┘    └───────────────┘      │
│                                                      │              │
│                                                      ▼              │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────────┐      │
│  │  Synthesizer │◀───│  Extractor   │◀───│   Analyzer    │      │
│  │   Agent     │    │   Agent      │    │   Agent       │      │
│  └──────────────┘    └──────────────┘    └───────────────┘      │
│         │                                                      │
│         ▼                                                      │
│  ┌──────────────┐                                               │
│  │  Formatter   │                                               │
│  │   Agent     │                                               │
│  └──────────────┘                                               │
│                                                                      │
│  Output: Professional Summary in Multiple Formats                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## The 5 Agents

| Agent | Function | Output |
|-------|----------|--------|
| **Scanner** | Discover and catalog ebooks | File metadata |
| **Parser** | Extract text from EPUB/PDF | Raw text |
| **Analyzer** | Identify key themes & structure | Chapter summaries |
| **Extractor** | Pull key insights & quotes | Important passages |
| **Synthesizer** | Create condensed summary | Bullet points |
| **Formatter** | Polish and export | Final document |

## Use Cases

### 1. Busy Professionals
- Quick knowledge acquisition
- 15-minute book summaries
- Audio versions for commute

### 2. Researchers
- Fast literature review
- Cross-book comparisons
- Citation extraction

### 3. Students
- Exam preparation
- Concept explanations
- Key takeaways

### 4. Book Clubs
- Discussion guides
- Author background
- Thematic analysis

## Installation

```bash
# Create project directory
mkdir -p ~/ebook-summarizer
cd ~/ebook-summarizer

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p data/ebooks data/summaries data/cache logs

# Copy environment template
cp .env.example .env
```

## Requirements

```
# requirements.txt
ebooklib>=0.18
beautifulsoup4>=4.12.0
lxml>=4.9.0
pdfminer.six>=20221105
pypdf>=3.0.0
ollama>=0.1.0
langchain>=0.1.0
langchain-community>=0.0.0
chromadb>=0.4.0
tqdm>=4.65.0
pydantic>=2.5.0
python-dotenv>=1.0.0
pyttsx3>=2.90
reportlab>=4.0.0
```

## Configuration

```bash
# .env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5-coder
EMBEDDING_MODEL=nomic-embed-text

# Processing
MAX_WORKERS=4
BATCH_SIZE=10
CHUNK_SIZE=5000
SUMMARY_RATIO=0.05

# Paths
EBOOKS_PATH=/data/ebooks
SUMMARIES_PATH=/data/summaries

# Summary Style
VOICE=professional
OUTPUT_FORMAT=markdown
```

## Processing Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    Processing Pipeline                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. SCAN                                                         │
│     └── Find all EPUB/PDF files                                 │
│     └── Build file index with metadata                          │
│                                                                  │
│  2. PARSE                                                        │
│     └── Extract text from each format                            │
│     └── Handle encoding and structure                           │
│                                                                  │
│  3. ANALYZE                                                      │
│     └── Identify chapters and sections                          │
│     └── Detect key topics and themes                            │
│                                                                  │
│  4. EXTRACT                                                      │
│     └── Find important passages                                 │
│     └── Extract key concepts and definitions                    │
│                                                                  │
│  5. SYNTHESIZE                                                   │
│     └── Create bullet-point summaries                           │
│     └── Maintain 5% ratio                                       │
│                                                                  │
│  6. FORMAT                                                       │
│     └── Polish final output                                     │
│     └── Generate multiple formats                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Performance

| Metric | Value |
|--------|-------|
| Books Processed/Day | ~500 |
| Avg Summary Time | 5-10 min/book |
| Output Size | 5% of original |
| Memory Usage | 8-16GB |
| Storage/Summary | ~50KB |

## Quick Start

```bash
# Enable performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Start Ollama
ollama serve &

# Pull models
ollama pull qwen2.5-coder
ollama pull nomic-embed-text

# Scan library
python main.py scan --path /data/ebooks

# Process specific book
python main.py process "book title"

# Process entire library
python main.py batch --limit 100
```

## Output Examples

### Summary Output (Markdown)

```markdown
# Book Title: The Pragmatic Programmer

## Executive Summary
[3-5 sentence overview]

## Key Takeaways

### Fundamentals
- **DRY (Don't Repeat Yourself)**: Every piece of knowledge should have a single, unambiguous representation
- **Orthogonality**: Keep unrelated things unrelated; design components that are self-contained
- **Automation**: Eliminate manual steps wherever possible

### Code Design
- **Composition over Inheritance**: Prefer object composition over class inheritance
- **Law of Demeter**: Only talk to immediate friends; minimize coupling
- **YAGNI**: You aren't gonna need it - avoid speculative coding

### Professional Practices
- **Test Early, Test Often**: Continuous testing catches bugs early
- **Refactor Mercilessly**: Continuously improve code quality
- **Communicate**: Effective communication is as important as technical skills

## Key Concepts
- [Concept 1]
- [Concept 2]
- [Concept 3]

## Quotes
> "Quote 1" - Page XX
> "Quote 2" - Page XX

## Target Audience
[Who this book is best for]

## Read Time
Original: ~400 pages | Summary: ~20 pages (5%)
```

## Next Steps

- [EPUB Processor](./12-epub-processor.md) - Parse and extract text
- [Multi-Agent System](./13-multi-agent-system.md) - Agent architecture
- [Summary Generation](./14-summary-generation.md) - AI synthesis
- [Production Deployment](./15-production-deployment.md) - Scale up
