# Advanced RAG Techniques

## Table of Contents

1. [Introduction](#introduction)
2. [Chunking Strategies](#chunking-strategies)
3. [Retrieval Strategies](#retrieval-strategies)
4. [Context Enrichment](#context-enrichment)
5. [Advanced Patterns](#advanced-patterns)

## Introduction

Advanced RAG goes beyond simple similarity search to create more accurate and context-aware retrieval systems.

## Chunking Strategies

### Fixed Size Chunking

```python
from langchain.text_splitter import CharacterTextSplitter

text_splitter = CharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
    separator="\n"
)

chunks = text_splitter.split_text(document)
```

### Semantic Chunking

```python
from langchain.text_splitter import SemanticChunker
from langchain_ollama import OllamaEmbeddings

embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")

text_splitter = SemanticChunker(
    embeddings,
    breakpoint_threshold_type="percentile"
)

chunks = text_splitter.split_text(document)
```

### Document-Aware Chunking

```python
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Split by headers
headers_to_split_on = [
    ("#", "Header 1"),
    ("##", "Header 2"),
    ("###", "Header 3"),
]

markdown_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=headers_to_split_on
)

md_chunks = markdown_splitter.split_text(markdown_document)

# Then split large chunks
recursive_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)

final_chunks = recursive_splitter.split_documents(md_chunks)
```

## Retrieval Strategies

### Similarity Search

```python
# Basic similarity
results = vectorstore.similarity_search(query, k=5)
```

### Similarity with Threshold

```python
# Only return results above threshold
results = vectorstore.similarity_search_with_score(
    query,
    k=10,
    filter=lambda x: x.get("score", 1) > 0.7
)
```

### MMR (Max Marginal Relevance)

```python
# Diversify results
results = vectorstore.max_marginal_relevance_search(
    query,
    k=5,
    fetch_k=20  # Fetch more, select diverse
)
```

### Hybrid Search (Vector + Keyword)

```python
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever

# BM25 retriever
bm25_retriever = BM25Retriever.from_texts(chunks)
bm25_retriever.k = 3

# Vector retriever
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# Ensemble
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.3, 0.7]  # Weight keyword vs vector
)

results = ensemble_retriever.invoke(query)
```

## Context Enrichment

### Parent Document Retriever

```python
from langchain.retrievers import ParentDocumentRetriever
from langchain.text_splitter import RecursiveCharacterTextSplitter

# For small chunks
child_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=20
)

# For large chunks (parent)
parent_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100
)

retriever = ParentDocumentRetriever(
    vectorstore=vectorstore,
    docstore=InMemoryStore(),
    child_splitter=child_splitter,
    parent_splitter=parent_splitter
)

retriever.add_documents(documents)
```

### Contextual Compression

```python
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3.2:3b", temperature=0.3)

compressor = LLMChainExtractor.from_llm(llm)

compression_retriever = ContextualCompressionRetriever(
    base_compressor=compressor,
    base_retriever=vector_retriever
)

# Returns only relevant excerpts
results = compression_retriever.invoke(query)
```

### Self-Query Retriever

```python
from langchain.retrievers import SelfQueryRetriever
from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3.2:3b", temperature=0.3)

retriever = SelfQueryRetriever.from_llm(
    llm,
    vectorstore,
    document_contents="Technical documentation",
    metadata_field_info=[
        {"name": "source", "description": "Source document"},
        {"name": "page", "description": "Page number"}
    ]
)
```

## Advanced Patterns

### Multi-Query RAG

```python
from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate

llm = ChatOllama(model="llama3.2:3b", temperature=0.7)

# Generate multiple queries
def generate_queries(question):
    prompt = f"""Generate 3 different versions of this question:
{question}"""
    
    response = llm.invoke(prompt)
    queries = response.content.split("\n")[:3]
    return queries + [question]

# Retrieve for each
def multi_query_rag(question):
    queries = generate_queries(question)
    all_docs = []
    
    for q in queries:
        docs = vectorstore.similarity_search(q, k=3)
        all_docs.extend(docs)
    
    # Deduplicate
    unique_docs = list({doc.page_content: doc for doc in all_docs}.values())
    
    return unique_docs
```

### Multi-Hop RAG

```python
def multi_hop_rag(initial_query, hops=2):
    current_query = initial_query
    all_context = []
    
    for hop in range(hops):
        # Retrieve
        docs = vectorstore.similarity_search(current_query, k=3)
        context = "\n\n".join([doc.page_content for doc in docs])
        all_context.append(context)
        
        # Generate next query
        prompt = f"""Based on this context:
{context}

Generate a follow-up question to learn more:"""
        
        response = llm.invoke(prompt)
        current_query = response.content
    
    # Final answer
    final_prompt = f"""Question: {initial_query}

Context:
{chr(10).join(all_context)}

Answer:"""
    
    return llm.invoke(final_prompt)
```

### Routing RAG

```python
def route_query(query):
    # Determine which vectorstore to use
    if any(word in query.lower() for word in ["code", "programming", "function"]):
        return "code_store"
    elif any(word in query.lower() for word in ["spec", "hardware", "device"]):
        return "specs_store"
    else:
        return "general_store"

def routed_rag(query):
    store_name = route_query(query)
    
    if store_name == "code_store":
        store = code_vectorstore
    elif store_name == "spec_store":
        store = specs_vectorstore
    else:
        store = general_vectorstore
    
    docs = store.similarity_search(query, k=3)
    return docs
```

### Corrective RAG

```python
def corrective_rag(query):
    # Initial retrieval
    docs = vectorstore.similarity_search(query, k=5)
    
    # Check relevance
    context = "\n\n".join([doc.page_content for doc in docs])
    
    prompt = f"""Does this context answer the question?
Question: {query}
Context: {context}

Answer yes or no, and explain:"""
    
    response = llm.invoke(prompt)
    
    if "no" in response.content.lower():
        # Try different retrieval
        docs = vectorstore.max_marginal_relevance_search(query, k=5)
    
    return docs
```

## Next Steps

- [Hybrid Search](./06-hybrid-search.md) - Detailed hybrid implementation
- [Graph RAG](./07-graph-rag.md) - Knowledge graph integration
- [RAG Pipelines](./10-rag-pipelines.md) - Complete pipelines
