# Vector Databases for Jetson

## Table of Contents

1. [Introduction](#introduction)
2. [FAISS](#faiss)
3. [ChromaDB](#chromadb)
4. [Comparison](#comparison)
5. [Selection Guide](#selection-guide)

## Introduction

Vector databases store document embeddings for similarity search. On Jetson, we use lightweight, CPU-friendly options.

## FAISS

### Installation

```bash
pip install faiss-cpu
```

### Basic Usage

```python
import numpy as np
import faiss

# Create index
d = 384  # embedding dimension
index = faiss.IndexFlatL2(d)

# Add vectors
vectors = np.random.rand(100, d).astype('float32')
index.add(vectors)

# Search
query = np.random.rand(1, d).astype('float32')
k = 5
distances, indices = index.search(query, k)

print(f"Found {k} nearest neighbors")
print(f"Indices: {indices}")
print(f"Distances: {distances}")
```

### With LangChain

```python
from langchain_ollama import OllamaEmbeddings
from langchain.vectorstores import FAISS

embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")

# Create from texts
texts = [
    "Jetson AGX Orin is powerful",
    "CUDA enables GPU acceleration",
    "TensorRT optimizes inference"
]

vectorstore = FAISS.from_texts(texts, embeddings)

# Search
results = vectorstore.similarity_search("Jetson Orin", k=2)
for doc in results:
    print(doc.page_content)
```

### Save/Load

```python
# Save
vectorstore.save_local("faiss_index")

# Load
loaded_vs = FAISS.load_local(
    "faiss_index",
    embeddings,
    allow_dangerous_deserialization=True
)
```

## ChromaDB

### Installation

```bash
pip install chromadb
```

### Basic Usage

```python
import chromadb

# Create client
client = chromadb.Client()

# Create collection
collection = client.create_collection("my_docs")

# Add documents
collection.add(
    documents=[
        "Jetson AGX Orin specs",
        "CUDA programming guide",
        "TensorRT optimization"
    ],
    ids=["doc1", "doc2", "doc3"]
)

# Query
results = collection.query(
    query_texts=["Jetson Orin"],
    n_results=2
)

print(results)
```

### With LangChain

```python
from langchain_ollama import OllamaEmbeddings
from langchain.vectorstores import Chroma

embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")

vectorstore = Chroma.from_texts(
    texts=texts,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

# Search
results = vectorstore.similarity_search("CUDA", k=2)
```

### Metadata Filtering

```python
# Add with metadata
collection.add(
    documents=["doc1", "doc2"],
    metadatas=[{"source": "manual", "type": "spec"}, 
               {"source": "guide", "type": "tutorial"}],
    ids=["doc1", "doc2"]
)

# Filter
results = collection.query(
    query_texts=["optimization"],
    where={"type": "tutorial"},
    n_results=1
)
```

## Comparison

| Feature | FAISS | ChromaDB |
|---------|-------|----------|
| Installation | Easy | Easy |
| Dependencies | Minimal | More |
| Persistence | Manual | Built-in |
| Filtering | Limited | Advanced |
| Speed | Very Fast | Fast |
| Memory | Low | Medium |
| ARM64 Support | Yes | Yes |

## Selection Guide

### Use FAISS When:
- Simple similarity search needed
- Memory is constrained
- Need maximum performance
- No metadata filtering required
- Just need vector storage

### Use ChromaDB When:
- Need metadata filtering
- Want built-in persistence
- Need collection management
- Developing prototypes
- Need more features

## Performance Tips

### FAISS Optimization

```python
# Use IVF index for large datasets
nlist = 100  # number of clusters
quantizer = faiss.IndexFlatL2(d)
index = faiss.IndexIVFFlat(quantizer, d, nlist)
index.train(vectors)
index.add(vectors)

# Search
index.nprobe = 10  # number of clusters to search
```

### ChromaDB Optimization

```python
# Use hnsw for faster search
collection = client.create_collection(
    "my_docs",
    metadata={"hnsw:space": "cosine"}
)
```

## Next Steps

- [Knowledge Graphs](./04-knowledge-graphs.md) - Build graphs
- [Advanced RAG](./05-advanced-rag.md) - Implement RAG
