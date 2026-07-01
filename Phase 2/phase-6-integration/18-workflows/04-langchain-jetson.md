# LangChain on Jetson

## Table of Contents

1. [Introduction](#introduction)
2. [Ollama Integration](#ollama-integration)
3. [Vector Stores](#vector-stores)
4. [Embeddings](#embeddings)
5. [RAG Implementation](#rag-implementation)

## Introduction

This guide covers running LangChain specifically on Jetson AGX Orin with Ollama as the backend LLM.

## Ollama Integration

### Using langchain-ollama

```python
from langchain_ollama import ChatOllama, OllamaEmbeddings

# Chat model
llm = ChatOllama(
    model="llama3.2:3b",
    base_url="http://localhost:11434",
    temperature=0.7,
    num_gpu=1,
    repeat_penalty=1.1
)

# Embeddings for RAG
embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)

# Simple chat
response = llm.invoke("Hello from Jetson!")
print(response.content)
```

### Direct Ollama Client

```python
import ollama

# List available models
models = ollama.list()
print(models)

# Generate response
response = ollama.generate(
    model="llama3.2:3b",
    prompt="Explain CUDA on Jetson",
    options={
        "num_gpu": 1,
        "temperature": 0.5
    }
)
print(response['response'])
```

## Vector Stores

### FAISS (CPU-based, works on ARM64)

```python
from langchain_ollama import OllamaEmbeddings
from langchain_embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS

# Using Ollama embeddings
ollama_embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)

# Or use HuggingFace (CPU)
hf_embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={'device': 'cpu'}
)

# Create vector store
texts = [
    "Jetson AGX Orin has 64GB memory",
    "CUDA provides GPU acceleration",
    "JetPack includes TensorRT"
]

# Using Ollama embeddings
vectorstore = FAISS.from_texts(
    texts=texts,
    embedding=ollama_embeddings
)

# Search
query = "What GPU memory does Orin have?"
docs = vectorstore.similarity_search(query)
print(docs[0].page_content)
```

### ChromaDB

```python
from langchain_ollama import OllamaEmbeddings
from langchain.vectorstores import Chroma

embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)

vectorstore = Chroma.from_texts(
    texts=texts,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

# Query
result = vectorstore.similarity_search_with_score(
    "Tell me about CUDA",
    k=2
)
for doc, score in result:
    print(f"Score: {score:.3f} | Content: {doc.page_content}")
```

## Embeddings

### Available Ollama Embedding Models

| Model | Dimensions | Use Case |
|-------|------------|----------|
| nomic-embed-text | 768 | General purpose |
| mxbai-embed-large | 1024 | High quality |
| snowflake-arctic-embed | 1024 | Enterprise |

```python
# Generate embeddings
from langchain_ollama import OllamaEmbeddings

embeddings = OllamaEmbeddings(model="nomic-embed-text")

# Single text
vec = embeddings.embed_query("Jetson AGX Orin inference")
print(f"Embedding dimensions: {len(vec)}")

# Multiple texts
vecs = embeddings.embed_documents([
    "First document",
    "Second document"
])
print(f"Number of embeddings: {len(vecs)}")
```

## RAG Implementation

### Complete RAG Pipeline

```python
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.text_splitter import RecursiveCharacterTextSplitter

# 1. Load documents
from langchain_community.document_loaders import TextLoader

loader = TextLoader("jetson_docs.txt")
documents = loader.load()

# 2. Split text
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)
splits = text_splitter.split_documents(documents)

# 3. Create embeddings and vectorstore
embeddings = OllamaEmbeddings(model="nomic-embed-text")
vectorstore = FAISS.from_documents(
    documents=splits,
    embedding=embeddings
)

# 4. Create retriever
retriever = vectorstore.as_retriever(
    search_kwargs={"k": 3}
)

# 5. Create QA chain
llm = ChatOllama(
    model="llama3.2:3b",
    temperature=0.3
)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff"
)

# 6. Query
question = "How do I optimize Jetson for inference?"
result = qa_chain.invoke({"query": question})
print(result["result"])
```

### Hybrid RAG (FAISS + BM25)

```python
from langchain_ollama import OllamaEmbeddings
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain.vectorstores import FAISS
from langchain.schema import Document

# Document corpus
docs = [
    Document(page_content="Jetson AGX Orin specs", metadata={"source": "specs"}),
    Document(page_content="CUDA programming guide", metadata={"source": "cuda"}),
    Document(page_content="TensorRT optimization", metadata={"source": "trt"}),
]

# BM25 retriever
bm25_retriever = BM25Retriever.from_documents(docs)
bm25_retriever.k = 2

# FAISS retriever
embeddings = OllamaEmbeddings(model="nomic-embed-text")
faiss_store = FAISS.from_documents(docs, embeddings)
faiss_retriever = faiss_store.as_retriever(search_kwargs={"k": 2})

# Ensemble
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, faiss_retriever],
    weights=[0.5, 0.5]
)

# Use in RAG chain
results = ensemble_retriever.invoke("Jetson CUDA")
for doc in results:
    print(doc.page_content)
```

## Memory Optimization

```python
# Clear CUDA cache periodically
import torch

def optimize_jetson_memory():
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.synchronize()

# Use smaller models for embeddings
embeddings = OllamaEmbeddings(model="all-minilm:6v")  # Smaller than nomic
```

## Next Steps

- [Agents](./05-agents.md)
- [Workflows](./06-workflows.md)
