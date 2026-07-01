# Embedding Models for RAG

## Ollama Embeddings

| Model | Dimensions | Use Case | Command |
|-------|------------|----------|---------|
| nomic-embed-text | 768 | General RAG | `ollama pull nomic-embed-text:latest` |
| qwen3-embedding | 1024 | High quality | `ollama pull qwen3-embedding:latest` |
| embeddinggemma | 512 | Lightweight | `ollama pull embeddinggemma:latest` |

## Usage

```python
from langchain_ollama import OllamaEmbeddings

# Best general purpose
embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")

# Generate embedding
vec = embeddings.embed_query("Jetson AGX Orin")
print(f"Dimension: {len(vec)}")

# Batch embeddings
vecs = embeddings.embed_documents(["doc1", "doc2"])
```

## Selection Guide

- **nomic-embed-text**: Best overall balance
- **qwen3-embedding**: Higher quality, larger
- **embeddinggemma**: Fast, lightweight

## Next Steps

- [RAG Pipelines](./10-rag-pipelines.md)
- [Evaluation](./11-evaluation.md)
