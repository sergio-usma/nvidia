# Knowledge Graphs and Advanced RAG Overview

## Table of Contents

1. [What is a Knowledge Graph](#what-is-a-knowledge-graph)
2. [What is RAG](#what-is-rag)
3. [Why Use Knowledge Graphs with RAG](#why-use-knowledge-graphs-with-rag)
4. [Architecture Overview](#architecture-overview)
5. [Use Cases](#use-cases)

## What is a Knowledge Graph

A knowledge graph represents information as a graph structure with:
- **Nodes**: Entities (people, places, concepts)
- **Edges**: Relationships between entities
- **Properties**: Attributes of nodes and edges

Example:
```
(Machine Learning) --is_a--> (AI)
(Neural Network) --is_a--> (Machine Learning)
(Jetson) --runs_on--> (CUDA)
```

## What is RAG

RAG (Retrieval-Augmented Generation) combines:
1. **Retrieval**: Find relevant documents from a knowledge base
2. **Augmentation**: Add context to the prompt
3. **Generation**: Use LLM to generate answer

Benefits:
- Reduces hallucinations
- Provides up-to-date information
- Enables domain-specific knowledge
- Improves accuracy

## Why Use Knowledge Graphs with RAG

### Traditional RAG Limitations
- Flat document structure
- No understanding of relationships
- Lost context between chunks

### Knowledge Graph RAG Benefits
- Understands entity relationships
- Better context preservation
- More accurate retrieval
- Explainable AI

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     Jetson AGX Orin                        │
│                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐  │
│  │  Document   │───▶│   Embedding │───▶│   Vector     │  │
│  │   Loader    │    │    Model    │    │   Store      │  │
│  └─────────────┘    └─────────────┘    └──────────────┘  │
│                                            │               │
│                                            ▼               │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────┐  │
│  │  Knowledge  │◀───│   Graph     │◀───│   Entity     │  │
│  │   Graph     │    │   Builder   │    │   Extractor │  │
│  └─────────────┘    └─────────────┘    └──────────────┘  │
│         │                                               │
│         ▼                                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │              RAG Pipeline                        │    │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐  │    │
│  │  │ Retrieve │ + │ Augment  │ = │ Generate │  │    │
│  │  └──────────┘   └──────────┘   └──────────┘  │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                               │
│                           ▼                               │
│  ┌─────────────────────────────────────────────────┐    │
│  │                  LLM (Ollama/llama.cpp)         │    │
│  │  • qwen2.5-coder  • llama3.2  • mistral       │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Document Processing
- PDF, HTML, Markdown loaders
- Text chunking strategies
- Metadata extraction

### 2. Embedding Models
- Ollama embeddings
- HuggingFace embeddings
- Sentence transformers

### 3. Vector Databases
- FAISS (lightweight)
- ChromaDB (production)
- Weaviate (feature-rich)

### 4. Knowledge Graph
- Entity extraction
- Relationship mapping
- Graph storage (NetworkX, Neo4j)

### 5. RAG Pipeline
- Query processing
- Retrieval strategies
- Context building

## Use Cases

| Use Case | Description |
|----------|-------------|
| Enterprise Knowledge | Internal documentation, policies |
| Technical Support | Troubleshooting guides, FAQs |
| Research | Academic papers, experiments |
| Codebase | Documentation, API references |
| Customer Service | Product info, help articles |

## Next Steps

- [Environment Setup](./02-environment-setup.md) - Install dependencies
- [Vector Databases](./03-vector-databases.md) - Choose storage
- [Knowledge Graphs](./04-knowledge-graphs.md) - Build graphs
