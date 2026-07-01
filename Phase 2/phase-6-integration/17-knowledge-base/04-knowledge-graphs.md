# Building Knowledge Graphs

## Table of Contents

1. [Introduction](#introduction)
2. [Entity Extraction](#entity-extraction)
3. [Relationship Extraction](#relationship-extraction)
4. [Graph Construction](#graph-construction)
5. [Storage Options](#storage-options)

## Introduction

Knowledge graphs represent information as connected entities. They enhance RAG by understanding relationships between concepts.

## Entity Extraction

### Using spaCy

```python
import spacy

nlp = spacy.load("en_core_web_sm")

def extract_entities(text):
    doc = nlp(text)
    entities = []
    
    for ent in doc.ents:
        entities.append({
            "text": ent.text,
            "label": ent.label_,
            "start": ent.start_char,
            "end": ent.end_char
        })
    
    return entities

# Test
text = "Jetson AGX Orin runs on NVIDIA CUDA and TensorRT"
entities = extract_entities(text)
for e in entities:
    print(f"{e['text']} -> {e['label']}")
```

### Using LLM for Extraction

```python
import requests

def extract_entities_llm(text):
    prompt = f"""Extract entities from this text. 
Return as JSON list with 'text' and 'type'.

Text: {text}

Example: [{{"text": "Jetson", "type": "PRODUCT"}}]"""
    
    response = requests.post(
        "http://localhost:11434/v1/chat/completions",
        json={
            "model": "qwen2.5-coder:latest",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.3
        }
    )
    
    import json
    result = response.json()["choices"][0]["message"]["content"]
    # Parse JSON from response
    return json.loads(result)

entities = extract_entities_llm("NVIDIA Jetson AGX Orin uses CUDA")
print(entities)
```

## Relationship Extraction

### Pattern-Based

```python
import re

def extract_relationships(text):
    relationships = []
    
    # Common patterns
    patterns = [
        r"(\w+) is a (\w+)",
        r"(\w+) is part of (\w+)",
        r"(\w+) uses (\w+)",
        r"(\w+) runs on (\w+)",
        r"(\w+) supports (\w+)",
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            relationships.append({
                "source": match[0],
                "target": match[1],
                "type": "RELATED_TO"
            })
    
    return relationships

text = "Jetson AGX Orin is a GPU. It uses CUDA. TensorRT runs on Jetson."
rels = extract_relationships(text)
for r in rels:
    print(f"{r['source']} -> {r['type']} -> {r['target']}")
```

### LLM-Based

```python
def extract_relationships_llm(text):
    prompt = f"""Extract relationships from this text.
Return as JSON list with 'source', 'target', 'relationship'.

Text: {text}

Example: [{{"source": "Jetson", "target": "NVIDIA", "relationship": "manufacturer"}}]"""
    
    response = requests.post(
        "http://localhost:11434/v1/chat/completions",
        json={
            "model": "qwen2.5-coder:latest",
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    
    import json
    result = response.json()["choices"][0]["message"]["content"]
    return json.loads(result)
```

## Graph Construction

### Using NetworkX

```python
import networkx as nx

class KnowledgeGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
    
    def add_entity(self, entity_id, entity_type, properties=None):
        self.graph.add_node(
            entity_id,
            type=entity_type,
            **(properties or {})
        )
    
    def add_relationship(self, source, target, rel_type, properties=None):
        self.graph.add_edge(
            source,
            target,
            relationship=rel_type,
            **(properties or {})
        )
    
    def get_neighbors(self, entity, rel_type=None):
        if rel_type:
            return [
                (n, self.graph[entity][n]['relationship'])
                for n in self.graph.neighbors(entity)
                if self.graph[entity][n].get('relationship') == rel_type
            ]
        return list(self.graph.neighbors(entity))
    
    def get_subgraph(self, entity, depth=2):
        return nx.ego_graph(self.graph, entity, radius=depth)
    
    def to_cypher(self):
        """Generate Cypher queries for Neo4j"""
        queries = []
        
        # Nodes
        for node, data in self.graph.nodes(data=True):
            queries.append(
                f"CREATE (n:{data.get('type', 'Entity')} {{id: '{node}'}})"
            )
        
        # Edges
        for source, target, data in self.graph.edges(data=True):
            rel = data.get('relationship', 'RELATED_TO')
            queries.append(
                f"CREATE (a)-[:{rel}]->(b)"
            )
        
        return "\n".join(queries)

# Usage
kg = KnowledgeGraph()
kg.add_entity("Jetson AGX Orin", "Product", {"manufacturer": "NVIDIA"})
kg.add_entity("NVIDIA", "Company")
kg.add_entity("CUDA", "Technology")

kg.add_relationship("Jetson AGX Orin", "NVIDIA", "manufacturer")
kg.add_relationship("Jetson AGX Orin", "CUDA", "uses")

print(f"Nodes: {kg.graph.nodes()}")
print(f"Edges: {kg.graph.edges()}")
```

### From Documents

```python
def build_graph_from_documents(documents):
    """Build knowledge graph from document list"""
    kg = KnowledgeGraph()
    
    for doc in documents:
        # Extract entities
        entities = extract_entities_llm(doc.page_content)
        
        for entity in entities:
            kg.add_entity(
                entity['text'],
                entity.get('type', 'Entity'),
                {"source": doc.metadata.get('source', 'unknown')}
            )
        
        # Extract relationships
        relationships = extract_relationships_llm(doc.page_content)
        
        for rel in relationships:
            kg.add_relationship(
                rel['source'],
                rel['target'],
                rel.get('relationship', 'RELATED_TO')
            )
    
    return kg
```

## Storage Options

### Save as GraphML

```python
# Save to file
nx.write_graphml(kg.graph, "knowledge_graph.graphml")

# Load from file
loaded_graph = nx.read_graphml("knowledge_graph.graphml")
```

### Save as JSON

```python
import json

def to_json(kg):
    data = {
        "nodes": [
            {"id": n, **d} for n, d in kg.graph.nodes(data=True)
        ],
        "edges": [
            {"source": s, "target": t, **d}
            for s, t, d in kg.graph.edges(data=True)
        ]
    }
    return json.dumps(data, indent=2)

# Save
with open("graph.json", "w") as f:
    f.write(to_json(kg))
```

### In-Memory with ChromaDB

```python
# Store in ChromaDB with graph metadata
collection.add(
    documents=[doc.page_content],
    metadatas=[{
        "entity_ids": json.dumps(entity_ids),
        "relationship_count": len(relationships)
    }],
    ids=[doc_id]
)
```

## Visualization

```python
import matplotlib.pyplot as plt

def visualize(kg):
    pos = nx.spring_layout(kg.graph)
    
    # Draw nodes
    nx.draw_networkx_nodes(kg.graph, pos, node_color='lightblue')
    
    # Draw edges
    nx.draw_networkx_edges(kg.graph, pos, edge_color='gray')
    
    # Draw labels
    nx.draw_networkx_labels(kg.graph, pos)
    
    plt.show()

visualize(kg)
```

## Next Steps

- [Advanced RAG](./05-advanced-rag.md) - Use graphs in RAG
- [Hybrid Search](./06-hybrid-search.md) - Combine search methods
- [Graph RAG](./07-graph-rag.md) - Full implementation
