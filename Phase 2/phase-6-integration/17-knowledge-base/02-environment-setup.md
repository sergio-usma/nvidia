# Environment Setup

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Install Python Dependencies](#install-python-dependencies)
3. [Vector Database Installation](#vector-database-installation)
4. [Knowledge Graph Tools](#knowledge-graph-tools)
5. [Verify Installation](#verify-installation)

## System Requirements

- **Hardware**: Jetson AGX Orin 64GB
- **OS**: Ubuntu 22.04.5 LTS (aarch64)
- **JetPack**: 6.2.2
- **Python**: 3.10+
- **RAM**: 16GB+ recommended for RAG

## Install Python Dependencies

### Core Dependencies

```bash
pip install --upgrade pip

# Core ML/AI
pip install numpy scipy scikit-learn

# LangChain and related
pip install langchain langchain-community langchain-core

# Ollama integration
pip install langchain-ollama

# For embeddings
pip install sentence-transformers

# For document loading
pip install pypdf python-docx beautifulsoup4

# For text processing
pip install nltk spacy
python -m spacy download en_core_web_sm
```

### Vector Databases

```bash
# FAISS (lightweight, CPU-based)
pip install faiss-cpu

# ChromaDB (production-ready)
pip install chromadb

# Qdrant (optional, requires Docker)
# pip install qdrant
```

### Knowledge Graph Tools

```bash
# NetworkX for graph operations
pip install networkx

# spaCy for NER
pip install spacy
python -m spacy download en_core_web_sm

# Optional: Graph databases
# pip install neo4j  # For Neo4j integration
```

## Vector Database Installation

### FAISS (Recommended for Jetson)

```bash
# Install FAISS
pip install faiss-cpu

# Verify
python -c "import faiss; print('FAISS installed')"
```

### ChromaDB

```bash
# Install ChromaDB
pip install chromadb

# ChromaDB requires these dependencies
pip install onnxruntime
pip install mmh3
pip install posthog
```

### Check Dependencies

```python
# Test imports
import numpy as np
import faiss
import chromadb
print("All dependencies installed!")
```

## Knowledge Graph Tools

### spaCy for NER

```bash
# Install spaCy
pip install spacy
python -m spacy download en_core_web_sm

# Test
python -c "import spacy; nlp = spacy.load('en_core_web_sm'); print('spaCy ready')"
```

### NetworkX

```bash
# Install
pip install networkx

# Test
python -c "import networkx as nx; G = nx.Graph(); print('NetworkX ready')"
```

## Ollama Setup for RAG

### Install Embedding Models

```bash
# Pull embedding models
ollama pull nomic-embed-text:latest
ollama pull qwen3-embedding:latest
ollama pull embeddinggemma:latest

# Verify
curl http://localhost:11434/api/tags
```

### Verify Ollama API

```python
import requests

# Test embeddings
response = requests.post(
    "http://localhost:11434/v1/embeddings",
    json={
        "model": "nomic-embed-text:latest",
        "prompt": "test embedding"
    }
)
print(response.json())
```

## Verify Installation

### Basic Test

```python
import numpy as np
import faiss
import requests

# Test FAISS
d = 128
index = faiss.IndexFlatL2(d)
print(f"FAISS index created: {index.ntotal} vectors")

# Test Ollama
resp = requests.get("http://localhost:11434/api/tags")
print(f"Ollama models: {resp.json()}")

print("\n✅ All dependencies ready!")
```

### Full RAG Test

```python
from langchain_ollama import OllamaEmbeddings
from langchain.vectorstores import FAISS

# Test embedding
embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")
vec = embeddings.embed_query("test")
print(f"Embedding dimension: {len(vec)}")

# Test vector store
vs = FAISS.from_texts(
    ["test doc"],
    embedding=embeddings
)
print("✅ Vector store created")
```

## Performance Optimization

### Enable Max Performance

```bash
sudo nvpmodel -m 0
sudo jetson_clocks
```

### Memory Management

```bash
# Check available memory
free -h

# Clear cache if needed
sync && echo 3 | sudo tee /proc/sys/vm/drop_caches
```

## Next Steps

- [Vector Databases](./03-vector-databases.md) - Choose storage
- [Knowledge Graphs](./04-knowledge-graphs.md) - Build graphs
- [Advanced RAG](./05-advanced-rag.md) - Implement RAG
