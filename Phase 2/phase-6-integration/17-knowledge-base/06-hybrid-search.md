# Hybrid Search Implementation

## Table of Contents

1. [Introduction](#introduction)
2. [BM25 Search](#bm25-search)
3. [Vector Search](#vector-search)
4. [Ensemble Retriever](#ensemble-retriever)
5. [Rank Fusion](#rank-fusion)

## Introduction

Hybrid search combines keyword (BM25) and semantic (vector) search for better retrieval.

## BM25 Search

### Installation

```bash
pip install rank-bm25
```

### Basic BM25

```python
from rank_bm25 import BM25Okapi
import re

class BM25Search:
    def __init__(self, documents):
        # Tokenize
        self.tokenized = [self._tokenize(doc) for doc in documents]
        self.documents = documents
        self.bm25 = BM25Okapi(self.tokenized)
    
    def _tokenize(self, text):
        return re.findall(r'\w+', text.lower())
    
    def search(self, query, k=5):
        tokenized_query = self._tokenize(query)
        scores = self.bm25.get_scores(tokenized_query)
        
        # Get top k indices
        top_indices = sorted(range(len(scores)), 
                           key=lambda i: scores[i], 
                           reverse=True)[:k]
        
        return [
            (self.documents[i], scores[i])
            for i in top_indices
        ]

# Usage
docs = [
    "Jetson AGX Orin specs",
    "CUDA programming guide",
    "TensorRT optimization"
]

bm25 = BM25Search(docs)
results = bm25.search("Jetson Orin GPU")
for doc, score in results:
    print(f"Score: {score:.2f} | {doc}")
```

## Vector Search

```python
from langchain_ollama import OllamaEmbeddings
from langchain.vectorstores import FAISS

class VectorSearch:
    def __init__(self, documents, embedding_model="nomic-embed-text:latest"):
        self.embeddings = OllamaEmbeddings(model=embedding_model)
        self.vectorstore = FAISS.from_texts(
            documents,
            self.embeddings
        )
    
    def search(self, query, k=5):
        docs = self.vectorstore.similarity_search_with_score(query, k=k)
        return [(doc.page_content, score) for doc, score in docs]
    
    def search_vector(self, query, k=5):
        query_vector = self.embeddings.embed_query(query)
        docs = self.vectorstore.similarity_search_by_vector(query_vector, k=k)
        return [doc.page_content for doc in docs]

# Usage
vector_search = VectorSearch(docs)
results = vector_search.search("Jetson GPU")
```

## Ensemble Retriever

### Using LangChain

```python
from langchain.retrievers import EnsembleRetriever
from langchain_community.retrievers import BM25Retriever
from langchain.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings

# BM25 retriever
bm25_retriever = BM25Retriever.from_texts(
    chunks,
    preprocess_func=lambda x: x.lower().split()
)
bm25_retriever.k = 5

# Vector retriever
embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")
vectorstore = FAISS.from_texts(chunks, embeddings)
vector_retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

# Ensemble
ensemble = EnsembleRetriever(
    retrievers=[bm25_retriever, vector_retriever],
    weights=[0.3, 0.7]  # BM25:Vector
)

results = ensemble.invoke("Jetson CUDA optimization")
```

## Rank Fusion

### Reciprocal Rank Fusion

```python
def reciprocal_rank_fusion(results_list, k=60):
    """Combine ranked lists using RRF"""
    scores = {}
    
    for results in results_list:
        for rank, (doc, score) in enumerate(results):
            if doc not in scores:
                scores[doc] = 0
            scores[doc] += 1 / (k + rank + 1)
    
    # Sort by score
    sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_results

def hybrid_search(query, k=5):
    # Get results from both methods
    bm25_results = bm25.search(query, k=k*2)
    vector_results = vector_search.search(query, k=k*2)
    
    # Combine
    combined = reciprocal_rank_fusion([
        bm25_results,
        [(doc, 1/score) for doc, score in vector_results]  # Convert distance to similarity
    ], k=k)
    
    return combined[:k]

# Usage
results = hybrid_search("CUDA Jetson")
for doc, score in results:
    print(f"RRF Score: {score:.3f} | {doc[:50]}...")
```

### Custom Fusion

```python
def custom_fusion(bm25_results, vector_results, alpha=0.5):
    """Weighted combination of scores"""
    scores = {}
    
    # Normalize BM25 scores
    max_bm25 = max(score for _, score in bm25_results) if bm25_results else 1
    
    for doc, score in bm25_results:
        scores[doc] = alpha * (score / max_bm25)
    
    # Normalize vector scores
    min_vec = min(score for _, score in vector_results) if vector_results else 1
    max_vec = max(score for _, score in vector_results) if vector_results else 1
    range_vec = max_vec - min_vec if max_vec != min_vec else 1
    
    for doc, score in vector_results:
        if doc not in scores:
            scores[doc] = 0
        # Convert distance to similarity
        similarity = 1 - (score - min_vec) / range_vec
        scores[doc] += (1 - alpha) * similarity
    
    return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

## Complete Hybrid Search Class

```python
class HybridSearch:
    def __init__(self, documents, embedding_model="nomic-embed-text:latest"):
        self.documents = documents
        
        # BM25
        self.bm25 = BM25Search(documents)
        
        # Vector
        self.vector = VectorSearch(documents, embedding_model)
    
    def search(self, query, k=5, method="rrf", alpha=0.5):
        if method == "rrf":
            # Reciprocal Rank Fusion
            bm25_results = self.bm25.search(query, k=k*2)
            vector_results = self.vector.search(query, k=k*2)
            results = reciprocal_rank_fusion([bm25_results, vector_results])
        elif method == "weighted":
            # Weighted combination
            bm25_results = self.bm25.search(query, k=k)
            vector_results = self.vector.search(query, k=k)
            results = custom_fusion(bm25_results, vector_results, alpha)
        else:
            # Simple ensemble
            results = self.vector.search(query, k=k)
        
        return results[:k]

# Usage
hybrid = HybridSearch(documents)
results = hybrid.search("Jetson AGX Orin", k=5, method="rrf")
```

## Performance Comparison

| Method | Pros | Cons |
|--------|------|------|
| BM25 | Fast, handles keywords | No semantic understanding |
| Vector | Semantic search | May miss keywords |
| Hybrid | Best of both | More complex, slower |

## Next Steps

- [Graph RAG](./07-graph-rag.md) - Use knowledge graphs
- [RAG Pipelines](./10-rag-pipelines.md) - Complete implementation
- [Evaluation](./11-evaluation.md) - Measure performance
