# Graph-Based RAG Systems

## Table of Contents

1. [Introduction](#introduction)
2. [GraphRAG Implementation](#graphrag-implementation)
3. [Entity-Based Retrieval](#entity-based-retrieval)
4. [Subgraph Retrieval](#subgraph-retrieval)
5. [Complete System](#complete-system)

## Introduction

GraphRAG combines knowledge graphs with vector search for more accurate retrieval.

## GraphRAG Implementation

```python
import networkx as nx
from langchain_ollama import OllamaEmbeddings
from langchain.vectorstores import FAISS
import requests

class GraphRAG:
    def __init__(self, documents):
        self.graph = nx.DiGraph()
        self.chunks = []
        self._build_graph(documents)
    
    def _extract_entities(self, text):
        """Extract entities using LLM"""
        prompt = f"""Extract entities from this text as JSON:
{text[:500]}
Return: [{{"entity": "name", "type": "TYPE"}}]"""
        
        response = requests.post(
            "http://localhost:11434/v1/chat/completions",
            json={"model": "qwen2.5-coder:latest", 
                  "messages": [{"role": "user", "content": prompt}],
                  "temperature": 0.3}
        )
        
        import json
        try:
            return json.loads(response.json()["choices"][0]["message"]["content"])
        except:
            return []
    
    def _build_graph(self, documents):
        # Create chunks and extract entities
        for i, doc in enumerate(documents):
            chunk_id = f"chunk_{i}"
            self.chunks.append(doc)
            
            # Add chunk node
            self.graph.add_node(chunk_id, type="chunk", content=doc)
            
            # Extract entities
            entities = self._extract_entities(doc)
            for ent in entities:
                entity_id = ent["entity"].lower().replace(" ", "_")
                
                # Add entity node
                if not self.graph.has_node(entity_id):
                    self.graph.add_node(entity_id, type="entity", 
                                       entity_type=ent["type"])
                
                # Connect chunk to entity
                self.graph.add_edge(chunk_id, entity_id, relationship="contains")
    
    def retrieve(self, query, k=3):
        # Vector search
        embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")
        vs = FAISS.from_texts(self.chunks, embeddings)
        docs = vs.similarity_search(query, k=k)
        
        # Get connected entities
        results = []
        for doc in docs:
            chunk_id = f"chunk_{self.chunks.index(doc.page_content)}"
            
            # Get connected entities
            entities = list(self.graph.neighbors(chunk_id))
            entity_info = []
            
            for ent in entities:
                ent_data = self.graph.nodes[ent]
                # Get related chunks
                related = list(self.graph.neighbors(ent))
                entity_info.append({
                    "entity": ent,
                    "type": ent_data.get("entity_type"),
                    "related_chunks": related[:3]
                })
            
            results.append({
                "chunk": doc.page_content,
                "entities": entity_info
            })
        
        return results
    
    def generate_answer(self, query):
        context = self.retrieve(query)
        
        # Build context
        context_text = "\n\n".join([
            f"Document:\n{c['chunk']}\nEntities: {c['entities']}"
            for c in context
        ])
        
        prompt = f"""Based on this context, answer the question.

Context:
{context_text}

Question: {query}

Answer:"""
        
        response = requests.post(
            "http://localhost:11434/v1/chat/completions",
            json={"model": "llama3.2:3b",
                  "messages": [{"role": "user", "content": prompt}]}
        )
        
        return response.json()["choices"][0]["message"]["content"]

# Usage
docs = [
    "Jetson AGX Orin uses CUDA for GPU acceleration.",
    "TensorRT provides inference optimization on Jetson.",
    "NVIDIA JetPack includes CUDA and TensorRT."
]

graph_rag = GraphRAG(docs)
answer = graph_rag.generate_answer("What optimizes inference on Jetson?")
print(answer)
```

## Entity-Based Retrieval

```python
def entity_based_retrieve(query, kg, vectorstore):
    # Find relevant entities
    prompt = f"What entities are relevant to: {query}"
    
    response = requests.post(
        "http://localhost:11434/v1/chat/completions",
        json={"model": "qwen2.5-coder:latest",
              "messages": [{"role": "user", "content": prompt}]}
    )
    
    # Extract entity names
    entities = response.json()["choices"][0]["message"]["content"]
    
    # Find chunks related to entities
    results = []
    for entity in entities.split(","):
        entity = entity.strip().lower().replace(" ", "_")
        if kg.graph.has_node(entity):
            related = list(kg.graph.neighbors(entity))
            for r in related:
                if kg.graph.nodes[r].get("type") == "chunk":
                    results.append(r)
    
    # Deduplicate and get content
    unique_results = list(set(results))
    chunks = [kg.chunks[int(r.split("_")[1])] for r in unique_results]
    
    return chunks[:5]
```

## Subgraph Retrieval

```python
def subgraph_retrieval(query, kg, depth=2):
    # Find starting entities
    entities = extract_entities(query)
    
    # Build subgraph for each entity
    all_subgraphs = []
    for entity in entities:
        entity_id = entity.lower().replace(" ", "_")
        if kg.graph.has_node(entity_id):
            subgraph = nx.ego_graph(kg.graph, entity_id, radius=depth)
            all_subgraphs.append(subgraph)
    
    # Combine subgraphs
    combined = nx.compose_all(all_subgraphs)
    
    return combined
```

## Next Steps

- [Multi-Modal RAG](./08-multi-modal-rag.md)
- [RAG Pipelines](./10-rag-pipelines.md)
- [Production](./12-production.md)
