# Part 23: Knowledge Graphs and Advanced RAGs

## Overview

This section covers building knowledge graphs and advanced RAG (Retrieval-Augmented Generation) systems on your Jetson AGX Orin 64GB for enterprise-grade AI applications.

## Available Guides

| File | Description |
|------|-------------|
| [01-overview.md](./01-overview.md) | Introduction to knowledge graphs and advanced RAGs |
| [02-environment-setup.md](./02-environment-setup.md) | Prerequisites and dependencies |
| [03-vector-databases.md](./03-vector-databases.md) | Vector database options for Jetson |
| [04-knowledge-graphs.md](./04-knowledge-graphs.md) | Building knowledge graphs |
| [05-advanced-rag.md](./05-advanced-rag.md) | Advanced RAG techniques |
| [06-hybrid-search.md](./06-hybrid-search.md) | Hybrid search implementations |
| [07-graph-rag.md](./07-graph-rag.md) | Graph-based RAG systems |
| [08-multi-modal-rag.md](./08-multi-modal-rag.md) | Multi-modal RAG applications |
| [09-embedding-models.md](./09-embedding-models.md) | Embedding model selection |
| [10-rag-pipelines.md](./10-rag-pipelines.md) | Complete RAG pipeline examples |
| [11-evaluation.md](./11-evaluation.md) | RAG evaluation metrics |
| [12-production.md](./12-production.md) | Production deployment |
| [13-troubleshooting.md](./13-troubleshooting.md) | Common issues and solutions |

## Quick Start

```bash
# 1. Install vector database (choose one)
pip install faiss-cpu  # Lightweight
pip install chromadb    # Production-ready

# 2. Install embedding models
ollama pull nomic-embed-text:latest
ollama pull qwen3-embedding:latest

# 3. Create a simple RAG
python create_rag.py
```

## Prerequisites

- Jetson AGX Orin 64GB
- JetPack 6.2.2
- Ollama or llama.cpp running
- 16GB+ RAM available for RAG

## Compatible Models

### Embedding Models (Ollama)
- `nomic-embed-text:latest` - Best general purpose
- `qwen3-embedding:latest` - High quality
- `embeddinggemma:latest` - Lightweight

### LLM Models for RAG
- `qwen2.5-coder:latest` - Code/technical RAG
- `llama3.2:3b` - General RAG
- `mistral:latest` - Fast RAG
- `deepseek-r1:8b` - Reasoning-heavy RAG

## Next Steps

Start with [01-overview.md](./01-overview.md) to understand the concepts.
